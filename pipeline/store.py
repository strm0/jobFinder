"""SQLite store for JobTech postings.

Raw first, deliberately. Each ad's full JobTech payload is kept verbatim as JSON and
only the handful of columns needed to find, partition and dedupe it are lifted out.
The normalised schema the matcher wants is built separately, by `pipeline/normalise.py`,
so that getting it wrong is a transformation over data already on disk rather than a
refetch of every ad.

See context/jobtech_fields.md for the field mapping and the traps.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "postings.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
    id                    TEXT PRIMARY KEY,
    payload               TEXT NOT NULL,
    is_tombstone          INTEGER NOT NULL DEFAULT 0,
    occupation_field_id   TEXT,
    occupation_group_id   TEXT,
    headline              TEXT,
    publication_date      TEXT,
    last_publication_date TEXT,
    timestamp_ms          INTEGER,
    removed               INTEGER NOT NULL DEFAULT 0,
    removed_date          TEXT,
    source                TEXT NOT NULL,
    first_seen            TEXT NOT NULL,
    last_seen             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ads_field    ON ads(occupation_field_id);
CREATE INDEX IF NOT EXISTS ads_removed  ON ads(removed);
CREATE INDEX IF NOT EXISTS ads_pubdate  ON ads(publication_date);

-- Where the JobStream consumer got to, so a restart does not refetch or skip.
CREATE TABLE IF NOT EXISTS stream_cursor (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    last_run_utc TEXT NOT NULL
);

-- One row per ingest run, so a gap in the data can be explained later.
CREATE TABLE IF NOT EXISTS ingest_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,
    started_utc TEXT NOT NULL,
    ended_utc   TEXT,
    seen        INTEGER NOT NULL DEFAULT 0,
    inserted    INTEGER NOT NULL DEFAULT 0,
    updated     INTEGER NOT NULL DEFAULT 0,
    closed      INTEGER NOT NULL DEFAULT 0,
    note        TEXT
);
"""


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path=DB_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def upsert(conn, ad, source):
    """Insert or update one ad. Returns 'inserted', 'updated' or 'closed'.

    A JobStream removal is a sparse tombstone: nine keys, no headline, no description.
    It must never overwrite a stored full payload, or the ad text is lost the moment
    the posting closes and the store becomes useless for anything but counting.
    """
    ad_id = ad["id"]
    removed = bool(ad.get("removed"))
    ts = now_utc()
    row = conn.execute("SELECT id, is_tombstone FROM ads WHERE id = ?", (ad_id,)).fetchone()

    if removed and row is not None:
        conn.execute(
            "UPDATE ads SET removed = 1, removed_date = ?, last_seen = ? WHERE id = ?",
            (ad.get("removed_date"), ts, ad_id),
        )
        return "closed"

    # A tombstone for an ad we never saw: keep it so the id is known, flagged so a
    # later full payload is allowed to replace it.
    if removed:
        conn.execute(
            """INSERT INTO ads (id, payload, is_tombstone, occupation_field_id,
                                occupation_group_id, removed, removed_date, source,
                                first_seen, last_seen)
               VALUES (?, ?, 1, ?, ?, 1, ?, ?, ?, ?)""",
            (
                ad_id,
                json.dumps(ad, ensure_ascii=False),
                (ad.get("occupation_field") or {}).get("concept_id"),
                (ad.get("occupation_group") or {}).get("concept_id"),
                ad.get("removed_date"),
                source,
                ts,
                ts,
            ),
        )
        return "inserted"

    fields = (
        json.dumps(ad, ensure_ascii=False),
        (ad.get("occupation_field") or {}).get("concept_id"),
        (ad.get("occupation_group") or {}).get("concept_id"),
        ad.get("headline"),
        ad.get("publication_date"),
        ad.get("last_publication_date"),
        ad.get("timestamp"),
        source,
        ts,
    )

    if row is None:
        conn.execute(
            """INSERT INTO ads (payload, occupation_field_id, occupation_group_id,
                                headline, publication_date, last_publication_date,
                                timestamp_ms, source, last_seen, id, is_tombstone,
                                removed, first_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)""",
            fields + (ad_id, ts),
        )
        return "inserted"

    conn.execute(
        """UPDATE ads SET payload = ?, occupation_field_id = ?, occupation_group_id = ?,
                          headline = ?, publication_date = ?, last_publication_date = ?,
                          timestamp_ms = ?, source = ?, last_seen = ?, is_tombstone = 0
           WHERE id = ?""",
        fields + (ad_id,),
    )
    return "updated"


def start_run(conn, kind, note=None):
    cur = conn.execute(
        "INSERT INTO ingest_runs (kind, started_utc, note) VALUES (?, ?, ?)",
        (kind, now_utc(), note),
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id, counts):
    conn.execute(
        """UPDATE ingest_runs SET ended_utc = ?, seen = ?, inserted = ?, updated = ?,
                                  closed = ? WHERE id = ?""",
        (
            now_utc(),
            counts.get("seen", 0),
            counts.get("inserted", 0),
            counts.get("updated", 0),
            counts.get("closed", 0),
            run_id,
        ),
    )
    conn.commit()


def get_cursor(conn):
    row = conn.execute("SELECT last_run_utc FROM stream_cursor WHERE id = 1").fetchone()
    return row["last_run_utc"] if row else None


def set_cursor(conn, when):
    conn.execute(
        """INSERT INTO stream_cursor (id, last_run_utc) VALUES (1, ?)
           ON CONFLICT(id) DO UPDATE SET last_run_utc = excluded.last_run_utc""",
        (when,),
    )
    conn.commit()


def summary(conn):
    return {
        "total": conn.execute("SELECT COUNT(*) c FROM ads").fetchone()["c"],
        "open": conn.execute("SELECT COUNT(*) c FROM ads WHERE removed = 0").fetchone()["c"],
        "closed": conn.execute("SELECT COUNT(*) c FROM ads WHERE removed = 1").fetchone()["c"],
        "tombstone_only": conn.execute(
            "SELECT COUNT(*) c FROM ads WHERE is_tombstone = 1"
        ).fetchone()["c"],
    }
