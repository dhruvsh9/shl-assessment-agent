"""Small local evaluator for hand-written/public trace JSON files.

Expected trace format:
{
  "messages": [{"role": "user", "content": "..."}],
  "expected": ["Assessment name", "Another name"]
}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.catalog import catalog_urls
from app.main import app


client = TestClient(app)


def evaluate(path: Path) -> dict[str, object]:
    trace = json.loads(path.read_text(encoding="utf-8"))
    response = client.post("/chat", json={"messages": trace["messages"]})
    data = response.json()
    urls_ok = all(item["url"] in catalog_urls() for item in data.get("recommendations", []))
    names = {item["name"].lower() for item in data.get("recommendations", [])}
    expected = {name.lower() for name in trace.get("expected", [])}
    recall = len(names & expected) / len(expected) if expected else None
    return {"file": str(path), "status": response.status_code, "urls_ok": urls_ok, "recall": recall, "reply": data.get("reply")}


def main() -> None:
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        raise SystemExit("Usage: python scripts/evaluate_public_traces.py traces/*.json")
    for path in paths:
        print(json.dumps(evaluate(path), indent=2))


if __name__ == "__main__":
    main()
