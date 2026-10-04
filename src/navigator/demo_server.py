"""Serve the local review page and the generated JSON files."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from navigator.corpus import load_addresses, repo_root

HOST = os.environ.get("NAVIGATOR_DEMO_HOST", "127.0.0.1")
PORT = int(os.environ.get("NAVIGATOR_DEMO_PORT", "8765"))
_FILES = {
    "/output/rules.json": "rules.json",
    "/output/lookups.json": "lookups.json",
    "/output/geocodes.json": "geocodes.json",
    "/output/changes.json": "changes.json",
}


def run_demo(_argv: list[str] | None = None) -> int:
    server = ThreadingHTTPServer((HOST, PORT), DemoHandler)
    print(f"http://{HOST}:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            page = Path(__file__).resolve().parent / "demo" / "index.html"
            self._send(page.read_bytes(), "text/html; charset=utf-8")
            return
        name = _FILES.get(path)
        if name is None:
            self.send_error(404)
            return
        file_path = repo_root() / "output" / name
        if not file_path.is_file():
            self.send_error(404)
            return
        body = _demo_geocodes(file_path) if name == "geocodes.json" else file_path.read_bytes()
        self._send(body, "application/json")

    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        view = memoryview(body)
        for start in range(0, len(body), 65536):
            self.wfile.write(view[start : start + 65536])


_GEOCODE_FIELDS = (
    "address_id",
    "street_address",
    "postal_city",
    "zip",
    "legal_state",
    "legal_county",
    "legal_city",
    "match_status",
)


def _demo_geocodes(path: Path) -> bytes:
    """Send the place fields the page displays, plus the assessor sample facts. The Census raw match stays in the cache file."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    samples = {item.address_id: item for item in load_addresses()}
    slim = {}
    for address_id, record in (payload.get("geocodes") or {}).items():
        item = {field: record.get(field) for field in _GEOCODE_FIELDS}
        sample = samples.get(address_id)
        if sample is not None:
            item["year_built"] = sample.year_built
            item["units"] = sample.units
            item["use_code"] = sample.use_code
            item["use_description"] = sample.use_description
            item["source_dataset"] = sample.source_dataset
            item["sample_retrieved_at"] = sample.retrieved_at
        slim[address_id] = item
    return json.dumps({"geocodes": slim}).encode("utf-8")
