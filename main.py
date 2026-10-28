#!/usr/bin/env python3
"""Serve an HTML file, or a whole website folder, in a browser.

    python serve.py

Then open http://127.0.0.1:8001

To use this for a different site, change SITE_PATH below and run it again.
No extra packages are required.
"""

from __future__ import annotations

import argparse
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

QUIZE_APP_2 = "index.html"

HOST = "0.0.0.0"
PORT = 8001

def resolve_site(raw: str) -> tuple[Path, str | None]:
    """Return the folder to serve, and a filename if '/' should be that one file."""
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = Path(__file__).resolve().parent / candidate
    candidate = candidate.resolve()

    if not candidate.exists():
        sys.exit(f"SITE_PATH does not exist:\n  {candidate}")

    if candidate.is_file():
        if candidate.suffix.lower() not in {".html", ".htm"}:
            sys.exit(f"SITE_PATH is not an HTML file:\n  {candidate}")
        return candidate.parent, candidate.name

    if candidate.is_dir():
        index = candidate / "index.html"
        if not index.is_file():
            sys.exit(
                "That folder has no index.html.\n"
                f"  {candidate}\n"
                "Either add index.html, or set SITE_PATH to a specific .html file."
            )
        return candidate, None

    sys.exit(f"SITE_PATH is not a file or folder:\n  {candidate}")


class SiteHandler(SimpleHTTPRequestHandler):
    # Set by the server before each request via the partial() below.
    single_file: str | None = None

    def __init__(self, *args, directory: str | None = None, single_file: str | None = None, **kwargs):
        self.single_file = single_file
        super().__init__(*args, directory=directory, **kwargs)

    def _serve_single_file_at_root(self) -> None:
        if not self.single_file:
            return
        parts = urlsplit(self.path)
        if parts.path in ("", "/"):
            self.path = urlunsplit(("", "", "/" + quote(self.single_file), parts.query, ""))

    def do_GET(self) -> None:  # noqa: N802
        self._serve_single_file_at_root()
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve_single_file_at_root()
        super().do_HEAD()

    def list_directory(self, path):  # noqa: ARG002
        # Don't publish a file listing when the site is hosted.
        self.send_error(404, "Not found")
        return None

    def end_headers(self) -> None:
        # See HTML edits as soon as you refresh.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))


class SiteServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the HTML site in SITE_PATH (or --path) on HOST:PORT."
    )
    parser.add_argument(
        "--path",
        default=os.environ.get("SITE_PATH", QUIZE_APP_2),
        help="HTML file or website folder. Default is the SITE_PATH variable.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", HOST),
        help="Interface to listen on. Default 0.0.0.0.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", str(PORT))),
        help="Port to listen on. Default 8001, or the PORT environment variable.",
    )
    args = parser.parse_args()

    directory, single_file = resolve_site(args.path)
    handler = partial(SiteHandler, directory=str(directory), single_file=single_file)

    try:
        httpd = SiteServer((args.host, args.port), handler)
    except OSError as exc:
        sys.exit(f"Could not listen on {args.host}:{args.port}\n  {exc}")

    shown = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    label = single_file or "index.html"
    print(f"Serving {directory / label}")
    print(f"Open  http://{shown}:{args.port}")
    if args.host in {"0.0.0.0", "::"}:
        print("Hosting: this is reachable on this machine's network address, same port.")
    print("Stop with Ctrl+C.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
