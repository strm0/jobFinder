"""The dashboard: a local page over the store, served on 127.0.0.1 only.

    python -m dashboard.serve                 # http://127.0.0.1:8787
    python -m dashboard.serve --open          # and open it in the browser
    python -m dashboard.serve --port 9000

The page design is chosen with --ui. `standard`, the default, is the category standard in
dashboard/standard, and every new feature goes to it. An earlier page design that is not in
this repository reads /api/, so that half of the API is still here. Build the
page once first, and again after any change under its folder:

    cd dashboard/standard && npm install && npm run build

Never bound to the network and never published anywhere. Makes no API call and spends
nothing. It writes three things only: a star, an applied mark or a removal in `posting_state`,
a visit in `dashboard_visits`, and a new `brief.md` in a folder in `applications/` named for
the company, the job title and the ad number, which it never overwrites. Needs pyyaml, because
it reads the config with it.

The API has two halves. /api/ answers exactly as the earlier design was built to read it. /api/v2/
answers the new design: `place` narrows a list to all, stockholm or outside, `new=1` narrows
it to the jobs from every run since the user last looked, a job counts as new from when it was
classified rather than when it was fetched, `view=rejected` lists the jobs the model put in no
lane, `view=applied` lists the jobs marked applied, which the other lists then leave out, and
`view=dismissed` lists the jobs removed since the last run, which every other list leaves out
for good. `source` narrows a list to all, platsbanken or other, the job sites JobAd Links
lists, and the overview names any site whose reader has stopped finding ad text. The
earlier design's /api/ answers for Platsbanken only. The rules are in dashboard/queries.py.

To work on a page itself, run this server and `npm run dev` in that page's folder side by
side. Vite serves the page on 127.0.0.1:5173 and passes /api through to here.
"""

import argparse
import json
import mimetypes
import re
import traceback
import webbrowser
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import briefs, demo, queries

HERE = Path(__file__).resolve().parent
# The page designs, by --ui name. Each is a Vite project whose build lands in its dist/.
UIS = {"standard": HERE / "standard"}
DEFAULT_UI = "standard"
API_V2 = "/api/v2/"
DEV_PORT = 5173
MAX_BODY = 64 * 1024
JOB_ID = re.compile(r"^[A-Za-z0-9-]{1,40}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$")

mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("text/javascript", ".js")


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def build_command(page):
    return f"cd {page.relative_to(HERE.parent)} && npm install && npm run build"


def handler_for(port, page):
    dist = page / "dist"
    # Only these Host headers are answered, which also shuts out DNS rebinding. Only the
    # page itself may call the API: a custom header forces a CORS preflight that this server
    # never grants, so another site open in the same browser cannot post here.
    hosts = {f"{name}:{p}" for name in ("127.0.0.1", "localhost") for p in (port, DEV_PORT)}
    origins = {f"http://{host}" for host in hosts}

    class Handler(BaseHTTPRequestHandler):
        server_version = "jobfinder-dashboard/1"

        def log_message(self, format, *args):
            pass  # quiet; a failure prints its own traceback below

        def do_GET(self):
            self.handle_request(write=False)

        def do_POST(self):
            self.handle_request(write=True)

        def handle_request(self, write):
            url = urlparse(self.path)
            try:
                if self.headers.get("Host") not in hosts:
                    raise HttpError(403, "This server only answers on localhost.")
                if url.path.startswith("/api/"):
                    self.check_api(write)
                    v2 = url.path.startswith(API_V2)
                    path = "/api/" + url.path[len(API_V2):] if v2 else url.path
                    rule = queries.CURRENT_RULE if v2 else queries.SPECIMEN_RULE
                    with closing(queries.connect()) as conn:
                        result = (self.post(conn, path, rule, v2) if write
                                  else self.get(conn, path, parse_qs(url.query), v2, rule))
                    self.send_json(200, result)
                elif write:
                    raise HttpError(405, "There is nothing to post to here.")
                elif url.path.startswith(demo.PREFIX):
                    # Only in the public copy: the sample ads are invented, so "open the
                    # ad" has no job site to go to and shows the stored text instead.
                    with closing(queries.connect()) as conn:
                        page = demo.ad_page(conn, unquote(url.path[len(demo.PREFIX):]))
                    self.send_bytes(200, page, "text/html; charset=utf-8", "no-store")
                else:
                    self.send_static(unquote(url.path))
            except HttpError as err:
                self.send_json(err.status, {"error": str(err)})
            except queries.BadRequest as err:
                self.send_json(400, {"error": str(err)})
            except queries.NotFound as err:
                self.send_json(404, {"error": str(err)})
            except queries.StoreError as err:
                self.send_json(503, {"error": str(err)})
            except Exception as err:
                traceback.print_exc()
                self.send_json(500, {"error": f"The server hit an error: {err}"})

        def check_api(self, write):
            if self.headers.get("X-Dashboard") != "1":
                raise HttpError(403, "Only the dashboard page can use this.")
            origin = self.headers.get("Origin")
            if origin is not None and origin not in origins:
                raise HttpError(403, "Only the dashboard page can use this.")
            if write and not (self.headers.get("Content-Type") or "").startswith("application/json"):
                raise HttpError(415, "Send JSON.")

        def get(self, conn, path, query, v2, rule):
            def one(name):
                return (query.get(name) or [None])[0]

            baseline = one("baseline")
            if baseline is not None and not TIMESTAMP.match(baseline):
                raise HttpError(400, "The baseline must be a timestamp.")
            # The earlier design never sends place, new or source, and is never offered them.
            place = (one("place") or "all") if v2 else "all"
            source = (one("source") or "all") if v2 else queries.SPECIMEN_SOURCE
            if path == "/api/overview":
                result = queries.overview(conn, baseline, rule=rule, place=place, short_names=v2,
                                          rejected_view=v2, applied_view=v2, dismissed_view=v2,
                                          source=source)
                if not v2:
                    return result
                return {**result, "place": place, "source": source,
                        "starredTotal": queries.starred_total(conn, dismissed_view=True),
                        "appliedTotal": queries.applied_total(conn),
                        "dismissedTotal": queries.dismissed_total(conn),
                        "readers": queries.reader_flags(conn)}
            if path == "/api/jobs":
                try:
                    page = int(one("page") or 1)
                except ValueError:
                    raise HttpError(400, "The page must be a number.") from None
                fresh = (one("new") or "0") if v2 else "0"
                if fresh not in ("0", "1"):
                    raise HttpError(400, "New must be 0 or 1.")
                offset = one("offset") if v2 else None
                if offset is not None and not re.fullmatch(r"[0-9]{1,9}", offset):
                    raise HttpError(400, "The offset must be a whole number.")
                result = queries.jobs(conn, one("view") or "top", one("lane") or "", page,
                                      baseline, rule=rule, place=place, only_new=fresh == "1",
                                      short_names=v2, rejected_view=v2, applied_view=v2,
                                      dismissed_view=v2,
                                      offset=None if offset is None else int(offset),
                                      source=source)
                return ({**result, "place": place, "onlyNew": fresh == "1", "source": source}
                        if v2 else result)
            raise HttpError(404, "There is no such endpoint.")

        def post(self, conn, path, rule, v2):
            body = self.read_body()
            if path == "/api/visit":
                return {"baseline": queries.record_visit(conn, rule=rule)}
            job_id = str(body.get("id", ""))
            if not JOB_ID.match(job_id):
                raise HttpError(400, "That is not a job id.")
            if path == "/api/star":
                return queries.set_star(conn, job_id, bool(body.get("starred")))
            if path == "/api/applied" and v2:
                return queries.set_applied(conn, job_id, bool(body.get("applied")))
            if path == "/api/dismiss" and v2:
                return queries.set_dismissed(conn, job_id, bool(body.get("dismissed")))
            if path == "/api/brief":
                return briefs.write(conn, job_id)
            raise HttpError(404, "There is no such endpoint.")

        def read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise HttpError(413, "That request is too large.")
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                raise HttpError(400, "The request body is not JSON.") from None
            if not isinstance(body, dict):
                raise HttpError(400, "The request body must be a JSON object.")
            return body

        def send_json(self, status, payload):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_bytes(status, data, "application/json; charset=utf-8", "no-store")

        def send_static(self, path):
            root = dist.resolve()
            if not (root / "index.html").is_file():
                note = f"The page is not built yet. Build it once with:\n\n    {build_command(page)}\n"
                self.send_bytes(503, note.encode(), "text/plain; charset=utf-8", "no-store")
                return
            target = (root / path.lstrip("/")).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                target = root / "index.html"   # the page draws its own views
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if kind.startswith("text/") or kind == "image/svg+xml":
                kind += "; charset=utf-8"
            cache = ("public, max-age=31536000, immutable" if target.parent.name == "assets"
                     else "no-cache")
            self.send_bytes(200, target.read_bytes(), kind, cache)

        def send_bytes(self, status, data, kind, cache):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--open", action="store_true", help="open the page in the default browser")
    ap.add_argument("--ui", choices=sorted(UIS), default=DEFAULT_UI,
                    help=f"which page design to serve, default {DEFAULT_UI}")
    args = ap.parse_args()
    page = UIS[args.ui]

    with closing(queries.connect()) as conn:
        queries.prepare(conn)
        warning = queries.location_warning(conn)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(args.port, page))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{args.port}/"
    print(f"dashboard, {args.ui} design, on {url}   Ctrl+C stops it")
    if warning:
        print(warning)
    if not (page / "dist" / "index.html").is_file():
        print(f"the page is not built yet: {build_command(page)}")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
