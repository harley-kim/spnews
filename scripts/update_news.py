from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "news.json"
KST = timezone(timedelta(hours=9))
TIMEOUT = 20
MAX_ITEMS = 160
UA = "SPNewsBot/1.0 (+https://github.com/harley-kim/spnews)"

BRAND_KEYWORDS = {
    "TAMRON": ["tamron"],
    "Voigtlander": ["voigtlander", "voigtländer", "cosina"],
    "Kenko": ["kenko"],
    "Tokina": ["tokina"],
    "SLIK": ["slik"],
    "BOYA": ["boya"],
    "Celestron": ["celestron"],
    "Sky-Watcher": ["sky-watcher", "skywatcher"],
    "DOMKE": ["domke"],
    "KODAK": ["kodak"],
    "HEIPI": ["heipi"],
    "SUNWAYFOTO": ["sunwayfoto"],
    "COLBOR": ["colbor"],
    "NEEWER": ["neewer"],
    "Gura Gear": ["gura gear", "guragear"],
    "Meade": ["meade"],
}

RSS_SOURCES = [
    {"name": "DPReview", "url": "https://www.dpreview.com/feeds/news.xml"},
    {"name": "Digital Camera Watch", "url": "https://dc.watch.impress.co.jp/data/rss/1.0/dcw/feed.rdf"},
    {"name": "PetaPixel", "url": "https://petapixel.com/feed/"},
]

OFFICIAL_PAGES = [
    {"name": "TAMRON Official", "url": "https://www.tamron.com/global/consumer/news/", "brand": "TAMRON"},
    {"name": "COSINA / Voigtlander", "url": "https://www.cosina.co.jp/news/", "brand": "Voigtlander"},
    {"name": "Celestron", "url": "https://www.celestron.com/blogs/news", "brand": "Celestron"},
]


def get(url: str) -> requests.Response:
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": UA, "Accept-Language": "en,ja;q=0.9,ko;q=0.8"})
    r.raise_for_status()
    return r


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", value).strip()


def guess_brand(text: str) -> str | None:
    low = text.lower()
    for brand, words in BRAND_KEYWORDS.items():
        if any(word in low for word in words):
            return brand
    return None


def parse_date(value) -> str:
    if not value:
        return datetime.now(KST).isoformat()
    try:
        dt = dtparser.parse(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).isoformat()
    except Exception:
        return datetime.now(KST).isoformat()


def make_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:18]


def collect_rss() -> list[dict]:
    out = []
    for src in RSS_SOURCES:
        try:
            parsed = feedparser.parse(src["url"], request_headers={"User-Agent": UA})
            for entry in parsed.entries[:40]:
                title = clean_text(entry.get("title"))
                summary = clean_text(entry.get("summary") or entry.get("description"))
                url = entry.get("link")
                if not title or not url:
                    continue
                brand = guess_brand(f"{title} {summary}")
                if not brand:
                    continue
                out.append({
                    "id": make_id(url),
                    "type": "news",
                    "brand": brand,
                    "source": src["name"],
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "published_at": parse_date(entry.get("published") or entry.get("updated")),
                })
        except Exception as e:
            print(f"RSS failed: {src['name']}: {e}")
    return out


def collect_official_pages() -> list[dict]:
    out = []
    for src in OFFICIAL_PAGES:
        try:
            r = get(src["url"])
            soup = BeautifulSoup(r.text, "html.parser")
            seen = set()
            for a in soup.find_all("a", href=True):
                title = clean_text(a.get_text(" ", strip=True))
                if len(title) < 12 or len(title) > 180:
                    continue
                href = urljoin(src["url"], a["href"])
                if href in seen or href == src["url"]:
                    continue
                seen.add(href)
                context = clean_text(a.parent.get_text(" ", strip=True) if a.parent else "")
                marker = (title + " " + context).lower()
                if not any(k in marker for k in ["news", "release", "lens", "camera", "product", "発売", "発表", "新製品", "レンズ"]):
                    continue
                out.append({
                    "id": make_id(href),
                    "type": "news",
                    "brand": src["brand"],
                    "source": src["name"],
                    "title": title,
                    "summary": context or "공식 홈페이지에서 자세한 내용을 확인하세요.",
                    "url": href,
                    "published_at": datetime.now(KST).isoformat(),
                })
                if len(out) >= 60:
                    break
        except Exception as e:
            print(f"Official page failed: {src['name']}: {e}")
    return out


def load_existing() -> list[dict]:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8")).get("items", [])
    except Exception:
        return []


def main():
    existing = [x for x in load_existing() if not str(x.get("id", "")).startswith("welcome-") and x.get("type") != "video"]
    items = existing + collect_rss() + collect_official_pages()
    dedup = {}
    for item in items:
        if item.get("url"):
            dedup[item["url"]] = item
    items = sorted(dedup.values(), key=lambda x: x.get("published_at", ""), reverse=True)[:MAX_ITEMS]
    payload = {"updated_at": datetime.now(KST).isoformat(), "items": items}
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(items)} items to {DATA_FILE}")


if __name__ == "__main__":
    main()
