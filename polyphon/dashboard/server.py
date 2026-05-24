"""Lightweight HTTP dashboard — serves metrics from SQLite."""

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_DB_PATH = Path("polyphon_metrics.db")
_STATIC = Path(__file__).parent / "static"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        routes = {
            "/": (_STATIC / "index.html", "text/html"),
            "/charts.js": (_STATIC / "charts.js", "application/javascript"),
        }
        if self.path in routes:
            path, content_type = routes[self.path]
            self._serve_file(path, content_type)
        elif self.path == "/api/metrics":
            self._serve_json(self._query_metrics())
        elif self.path == "/api/summary":
            self._serve_json(self._query_summary())
        else:
            self.send_error(404)

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(data)

    def _serve_json(self, data: object) -> None:
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _query_metrics(self) -> list[dict]:
        if not _DB_PATH.exists():
            return []
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT ts, job, provider, voice, characters, duration_ms,
                      audio_duration_s, file_size_bytes, cost_usd, success, silence_ms
               FROM synthesis ORDER BY ts DESC LIMIT 1000"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _query_summary(self) -> dict:
        if not _DB_PATH.exists():
            return {}
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row

        total = conn.execute("SELECT COUNT(*) as n FROM synthesis").fetchone()["n"]
        if total == 0:
            conn.close()
            return {}

        agg = conn.execute("""
            SELECT
                SUM(characters)        as total_chars,
                SUM(cost_usd)          as total_cost,
                SUM(audio_duration_s)  as total_audio_s,
                SUM(file_size_bytes)   as total_bytes,
                AVG(duration_ms)       as avg_latency_ms,
                SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failures
            FROM synthesis
        """).fetchone()

        by_provider = conn.execute("""
            SELECT provider,
                   COUNT(*)           as requests,
                   SUM(characters)    as chars,
                   SUM(cost_usd)      as cost,
                   AVG(duration_ms)   as avg_latency_ms,
                   SUM(audio_duration_s) as audio_s,
                   AVG(CAST(file_size_bytes AS REAL) / NULLIF(characters, 0)) as bytes_per_char
            FROM synthesis
            GROUP BY provider
        """).fetchall()

        by_job = conn.execute("""
            SELECT job,
                   COUNT(*)         as chunks,
                   SUM(characters)  as chars,
                   SUM(cost_usd)    as cost,
                   SUM(audio_duration_s) as audio_s,
                   MIN(ts)          as started_at
            FROM synthesis
            GROUP BY job
            ORDER BY started_at DESC
            LIMIT 10
        """).fetchall()

        conn.close()

        return {
            "total_requests": total,
            "total_chars": agg["total_chars"] or 0,
            "total_cost_usd": round(agg["total_cost"] or 0, 6),
            "total_audio_minutes": round((agg["total_audio_s"] or 0) / 60, 2),
            "total_size_kb": round((agg["total_bytes"] or 0) / 1024, 1),
            "avg_latency_ms": round(agg["avg_latency_ms"] or 0, 1),
            "success_rate": round(agg["successes"] / total * 100, 1),
            "by_provider": [dict(r) for r in by_provider],
            "by_job": [dict(r) for r in by_job],
        }

    def log_message(self, *args) -> None:  # type: ignore[override]
        pass  # suppress default access log


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the dashboard server."""
    server = HTTPServer((host, port), _Handler)
    print(f"Dashboard → http://{host}:{port}")
    server.serve_forever()
