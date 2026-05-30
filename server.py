"""
Meridian - AI Engineering Intelligence Platform
server.py: Lightweight HTTP server. Serves the dashboard SPA and a
JSON REST API backed by the local SQLite database.
"""

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import analyzer
import scanner

DASHBOARD_DIR = Path(__file__).parent / "dashboard"


def _json_response(handler, data, status: int = 200):
    body = json.dumps(data, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _parse_qs_single(qs: dict, key: str, default=None):
    vals = qs.get(key, [])
    return vals[0] if vals else default


class MeridianHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress default access log noise

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        qs     = parse_qs(parsed.query)

        # ── Static files ──────────────────────────────────────────────────────
        if path == "/" or path == "/index.html":
            self._serve_file(DASHBOARD_DIR / "index.html", "text/html")
            return

        if path == "/pitch" or path == "/pitch.html":
            self._serve_file(DASHBOARD_DIR / "pitch.html", "text/html")
            return

        # ── API routes ────────────────────────────────────────────────────────
        if path == "/api/summary":
            _json_response(self, analyzer.get_summary())

        elif path == "/api/chart/daily":
            days = int(_parse_qs_single(qs, "days", 30))
            _json_response(self, analyzer.get_daily_chart(days=days))

        elif path == "/api/projects":
            _json_response(self, analyzer.get_projects())

        elif path == "/api/sessions":
            limit   = int(_parse_qs_single(qs, "limit", 25))
            project = _parse_qs_single(qs, "project")
            _json_response(self, analyzer.get_sessions(limit=limit, project=project))

        elif path == "/api/recommendations":
            _json_response(self, analyzer.get_recommendations())

        elif path == "/api/roi":
            _json_response(self, analyzer.get_roi())

        elif path == "/api/models":
            _json_response(self, analyzer.get_model_distribution())

        elif path == "/api/scan":
            result = scanner.scan()
            _json_response(self, result)

        else:
            _json_response(self, {"error": "not found"}, status=404)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_response(404)
            self.end_headers()
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run(host: str = "localhost", port: int = 7777, open_browser: bool = True):
    # Perform initial scan before serving
    print("⚡ Meridian — scanning usage data…", flush=True)
    result = scanner.scan()
    print(
        f"   ✓ {result['files_scanned']} files scanned  "
        f"({result['files_skipped']} unchanged skipped)  "
        f"{result['messages_added']} messages indexed",
        flush=True,
    )

    server = HTTPServer((host, port), MeridianHandler)
    url = f"http://{host}:{port}"
    print(f"\n   Dashboard → {url}\n   Ctrl+C to stop\n", flush=True)

    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n   Stopped.", flush=True)
