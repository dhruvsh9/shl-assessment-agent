"""Scrape SHL Individual Test Solutions into app/data/shl_catalog.json.

The public SHL catalog changes over time and may require adjusting CSS selectors.
This script is deliberately conservative: it only keeps rows with a name, SHL URL,
and inferred test type, then writes the same schema consumed by the API.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.shl.com"
CATALOG_URLS = [
    "https://www.shl.com/solutions/products/product-catalog/",
    "https://www.shl.com/solutions/products/productcatalog/",
]
OUT_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "shl_catalog.json"

TYPE_RULES = [
    ("P", ["personality", "opq", "motivation", "mq"]),
    ("A", ["cognitive", "ability", "reasoning", "numerical", "verbal", "inductive"]),
    ("S", ["situational", "judgement", "judgment", "behavioral", "simulation", "skills assessment"]),
    ("L", ["language", "english"]),
    ("K", ["knowledge", "technical", "coding", "programming", "java", "python", "sql", "excel", "skills"]),
]


def fetch(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if response.ok:
            return response.text
    except requests.RequestException:
        return None
    return None


def infer_type(text: str) -> str:
    lower = text.lower()
    for test_type, terms in TYPE_RULES:
        if any(term in lower for term in terms):
            return test_type
    return "K"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "/solutions/products/product-catalog/view/" in href or "/solutions/products/productcatalog/view/" in href:
            links.append(urljoin(BASE_URL, href))
    return sorted(set(links))


def scrape_detail(url: str) -> dict[str, object] | None:
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(["h1", "h2"])
    name = clean(heading.get_text(" ")) if heading else ""
    if not name:
        return None
    for noise in ["SHL", "Product Catalog"]:
        name = name.replace(noise, "").strip(" -")
    main = soup.find("main") or soup.body or soup
    text = clean(main.get_text(" "))
    description = text[:700]
    keywords = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9+#.]{2,}", f"{name} {description}".lower())))[:80]
    return {
        "name": name,
        "url": url,
        "test_type": infer_type(f"{name} {description}"),
        "description": description,
        "keywords": keywords,
    }


def main() -> None:
    detail_links: set[str] = set()
    for catalog_url in CATALOG_URLS:
        html = fetch(catalog_url)
        if html:
            detail_links.update(extract_links(html))

    rows = []
    for link in sorted(detail_links):
        row = scrape_detail(link)
        if row:
            rows.append(row)

    if not rows:
        raise SystemExit("No catalog rows scraped. Check the catalog URL/selectors or use the seeded JSON.")

    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} assessments to {OUT_PATH}")


if __name__ == "__main__":
    main()
