import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).parent / "data" / "shl_catalog.json"


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").split())


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    with CATALOG_PATH.open("r", encoding="utf-8") as file:
        rows = json.load(file)

    seen_urls: set[str] = set()
    catalog: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("name") or not row.get("url") or not row.get("test_type"):
            continue
        if row["url"] in seen_urls:
            continue
        seen_urls.add(row["url"])
        keywords = row.get("keywords", [])
        row["search_text"] = _normalize(
            " ".join([row["name"], row.get("description", ""), row["test_type"], *keywords])
        )
        catalog.append(row)
    return catalog


@lru_cache(maxsize=1)
def catalog_urls() -> set[str]:
    return {item["url"] for item in load_catalog()}


def as_recommendation(item: dict[str, Any]) -> dict[str, str]:
    return {
        "name": item["name"],
        "url": item["url"],
        "test_type": item["test_type"],
    }


def find_by_name_or_alias(query: str) -> list[dict[str, Any]]:
    q = _normalize(query)
    alias_targets = {
        "gsa": "global skills assessment",
        "opq": "occupational personality questionnaire",
        "opq32": "occupational personality questionnaire",
        "opq32r": "occupational personality questionnaire",
        "mq": "motivation questionnaire",
    }
    target = alias_targets.get(q)
    if target:
        preferred = [item for item in load_catalog() if target in _normalize(item["name"])]
        if preferred:
            return preferred
    matches = []
    for item in load_catalog():
        name = _normalize(item["name"])
        keywords = [_normalize(k) for k in item.get("keywords", [])]
        if q == name or q in name or any(q == k or q in k for k in keywords):
            matches.append(item)
    return matches
