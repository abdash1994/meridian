"""
TokenLens - AI Engineering Intelligence Platform
server.py: Lightweight HTTP server with token auth and concurrent request handling.
"""

import json
import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

import analyzer
import scanner

DASHBOARD_DIR = Path(__file__).parent / "dashboard"
CONFIG_PATH   = Path.home() / ".tokenlens" / "config.json"

# ── Auth token ────────────────────────────────────────────────────────────────

def _load_or_create_token() -> str:
    """Load existing token or generate a new one on first run."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
            if cfg.get("token"):
                return cfg["token"]
        except Exception:
            pass
    token = secrets.token_urlsafe(24)
    CONFIG_PATH.write_text(json.dumps({"token": token}, indent=2))
    return token


AUTH_TOKEN: str = _load_or_create_token()


def _check_auth(qs: dict) -> bool:
    """Validate token from query param or skip for static HTML (token is embedded)."""
    return qs.get("token", [None])[0] == AUTH_TOKEN


# ── Helpers ───────────────────────────────────────────────────────────────────

def _json_response(handler, data, status: int = 200):
    body = json.dumps(data, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _parse_qs_single(qs: dict, key: str, default=None):
    vals = qs.get(key, [])
    return vals[0] if vals else default


def _serve_html(handler, path: Path):
    """Serve HTML file with auth token injected as a JS constant."""
    if not path.exists():
        handler.send_response(404)
        handler.end_headers()
        return
    content = path.read_text(encoding="utf-8").replace("__TL_TOKEN__", AUTH_TOKEN)
    body = content.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


# ── Threaded server (fixes single-threaded request queue) ────────────────────

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a separate thread."""
    daemon_threads = True


# ── Request handler ───────────────────────────────────────────────────────────

class TokenLensHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress noisy access log

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        qs     = parse_qs(parsed.query)

        # ── Static HTML (token injected server-side, no auth check needed) ───
        if path in ("/", "/index.html"):
            _serve_html(self, DASHBOARD_DIR / "index.html")
            return
        if path in ("/pitch", "/pitch.html"):
            _serve_html(self, DASHBOARD_DIR / "pitch.html")
            return

        # ── All API routes require token ──────────────────────────────────────
        if not _check_auth(qs):
            _json_response(self, {"error": "unauthorized"}, status=401)
            return

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
            dev_rate    = float(_parse_qs_single(qs, "dev_rate", analyzer.DEV_HOURLY_RATE))
            attribution = float(_parse_qs_single(qs, "attribution", analyzer.ATTRIBUTION_RATE))
            _json_response(self, analyzer.get_recommendations())

        elif path == "/api/roi":
            dev_rate    = float(_parse_qs_single(qs, "dev_rate", analyzer.DEV_HOURLY_RATE))
            attribution = float(_parse_qs_single(qs, "attribution", analyzer.ATTRIBUTION_RATE))
            _json_response(self, analyzer.get_roi(dev_hourly_rate=dev_rate, attribution_rate=attribution))

        elif path == "/api/models":
            _json_response(self, analyzer.get_model_distribution())

        elif path == "/api/scan":
            result = scanner.scan()
            _json_response(self, result)

        elif path == "/api/roadmap":
            _json_response(self, analyzer.get_roadmap_to_a())

        elif path == "/api/prune":
            before = _parse_qs_single(qs, "before")
            if not before:
                _json_response(self, {"error": "missing ?before=YYYY-MM-DD"}, status=400)
            else:
                result = analyzer.prune_before(before)
                _json_response(self, result)

        else:
            _json_response(self, {"error": "not found"}, status=404)


# ── Entry point ───────────────────────────────────────────────────────────────

def run(host: str = "localhost", port: int = 7777, open_browser: bool = True):
    print("⚡ TokenLens — scanning usage data…", flush=True)
    result = scanner.scan()
    print(
        f"   ✓ {result['files_scanned']} files scanned  "
        f"({result['files_skipped']} unchanged skipped)  "
        f"{result['messages_added']} messages indexed",
        flush=True,
    )

    server = ThreadedHTTPServer((host, port), TokenLensHandler)
    url    = f"http://{host}:{port}"
    print(f"\n   Dashboard → {url}", flush=True)
    print(f"   Ctrl+C to stop\n", flush=True)

    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n   Stopped.", flush=True)
