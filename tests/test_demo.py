"""A smoke test over the free path: seed a store from sample/, then check what the free
stages and the dashboard's queries make of it. No API, no key, nothing spent.

    python -m unittest -v

The store is built in a temporary folder, so this never touches data/postings.db.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import classify, prefilter, score, seed, store  # noqa: E402
from dashboard import queries  # noqa: E402  also puts tools/ on the path
import top  # noqa: E402


class DemoStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "postings.db"
        cls.patches = [mock.patch.object(store, "DB_PATH", cls.db),
                       mock.patch.object(queries, "DB", cls.db),
                       mock.patch.object(top, "DB", cls.db)]
        for p in cls.patches:
            p.start()
        cls.log = io.StringIO()
        with contextlib.redirect_stdout(cls.log):
            cls.seed_result = seed.seed()
        cls.conn = store.connect(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    def one(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()[0]

    def test_seed_builds_a_store_whose_own_checks_all_pass(self):
        self.assertEqual(self.seed_result, 0, self.log.getvalue())
        self.assertNotIn("FAIL", self.log.getvalue())

    def test_prefilter_skips_most_ads_and_rescues_some(self):
        keep = self.one("""SELECT COUNT(*) FROM prefilter f JOIN postings p ON p.id = f.id
                           WHERE p.removed = 0 AND f.verdict = 'keep'""")
        total = self.one("SELECT COUNT(*) FROM postings WHERE removed = 0")
        self.assertTrue(0.30 <= keep / total <= 0.50, f"{keep} of {total} reach the model")
        self.assertGreater(self.one("SELECT COUNT(*) FROM prefilter WHERE reason LIKE 'rescue:%'"), 0)
        self.assertGreater(self.one("SELECT COUNT(*) FROM prefilter WHERE reason LIKE 'veto:%'"), 0)
        self.assertGreater(self.one("SELECT COUNT(*) FROM prefilter WHERE reason LIKE 'twin:%'"), 0)
        self.assertGreater(
            self.one("SELECT COUNT(*) FROM prefilter WHERE reason LIKE 'group_unknown:%'"), 0)

    def test_group_table_is_96_of_159(self):
        verdicts = prefilter.load_verdicts()
        self.assertEqual(len(verdicts), 159)
        self.assertEqual(sum(1 for v in verdicts.values() if v == "skip"), 96)

    def test_the_score_is_not_an_average(self):
        rules = score.Rules.load()
        dream, easy = rules.recommend(9, 1), rules.recommend(0, 8)
        self.assertEqual(easy, 0)                       # want 0 is never a recommendation
        self.assertGreater(dream, easy)                 # a mean would put them side by side
        self.assertNotAlmostEqual(dream, (9 + 1) / 2)
        self.assertLessEqual(rules.recommend(7, 10), 7 * 1.15 + 1e-9)   # reach only discounts
        differs = self.one("""SELECT COUNT(*) FROM scores
                              WHERE want > 0 AND ABS(recommend - (want + reach) / 2.0) > 0.01""")
        self.assertGreater(differs, 0)

    def test_the_ranking_is_ordered_and_not_empty(self):
        rows = self.conn.execute(
            """SELECT s.recommend FROM scores s JOIN postings p ON p.id = s.id
               WHERE s.eligible = 1 AND s.repost_of IS NULL AND p.removed = 0
               ORDER BY s.recommend DESC""").fetchall()
        self.assertGreater(len(rows), 20)
        self.assertGreater(rows[0][0], rows[-1][0])

    def test_rejections_carry_their_reason(self):
        for prefix in ("hard_filter:", "no_lane_matched"):
            n = self.one("SELECT COUNT(*) FROM scores WHERE reject_reason LIKE ?", prefix + "%")
            self.assertGreater(n, 0, prefix)
        self.assertGreater(self.one("SELECT COUNT(*) FROM scores WHERE repost_of IS NOT NULL"), 0)

    def test_the_ratings_match_the_brief_and_prompt_as_shipped(self):
        stored = {r[0] for r in self.conn.execute(
            "SELECT DISTINCT classifier_version FROM classifications")}
        self.assertEqual(stored, {classify.classifier_version(classify.load_config())})

    def test_every_rating_is_the_models_own_json(self):
        for (raw,) in self.conn.execute("SELECT judgement FROM classifications"):
            parsed = json.loads(raw)
            self.assertIn(parsed["want"], range(11))
            self.assertIn(parsed["reach"], range(11))

    def test_classify_refuses_kindly_without_a_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(classify.KEY_VARIABLE, None)
            with self.assertRaises(SystemExit) as stop:
                classify.api_key()
        self.assertIn("pipeline.seed", str(stop.exception))
        self.assertIn("nothing was spent", str(stop.exception))

    def test_the_dashboard_has_something_to_show(self):
        conn = queries.connect()
        try:
            queries.prepare(conn)
            self.assertIsNone(queries.location_warning(conn))
            baseline = queries.record_visit(conn, rule=queries.CURRENT_RULE)
            view = dict(rule=queries.CURRENT_RULE, short_names=True, rejected_view=True,
                        applied_view=True, dismissed_view=True, source="all")
            overview = queries.overview(conn, baseline, **view)
            self.assertIsNone(overview["warning"])
            self.assertEqual(len(overview["lanes"]), 7)
            self.assertGreater(overview["counts"]["top"], 10)
            self.assertGreater(overview["counts"]["phd"], 0)
            self.assertGreater(overview["newCounts"]["top"], 0)
            page = queries.jobs(conn, "top", "", 1, baseline, **view)
            self.assertEqual(len(page["jobs"]), page["pageSize"])
            scores = [job["score"] for job in page["jobs"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            stockholm = queries.jobs(conn, "top", "", 1, baseline, place="stockholm", **view)
            self.assertTrue(0 < stockholm["total"] < page["total"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
