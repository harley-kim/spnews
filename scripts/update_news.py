from __future__ import annotations

import hashlib
import html
import json
import os
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

YOUTUBE_QUERIES = {
    "TAMRON": "탐론 렌즈 리뷰",
    "Voigtlander": "보이그랜더 렌즈 리뷰",
    "Celestron": "셀레스트론 리뷰",
    "BOYA": "BOYA 마이크 리뷰",
    "SLIK": "SLIK 삼각대 리뷰",
    "Kenko": "Kenko 필터 리뷰",
}


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


def translate_ko(title: str, summary: str) -> tuple[str, str]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return title, summary
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    prompt = (
        "You translate camera, lens, optics and audiovisual industry news into natural Korean. "
        "Use terminology Korean photographers actually use. Do not add facts. "
        "Return strict JSON with keys title and summary. Summary should be 1-2 concise Korean sentences.\n\n"
        f"TITLE: {title}\nSUMMARY: {summary[:1800]}"
    )
    try:
        r = requests.post(endpoint, timeout=35, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}})
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw)
        return clean_text(data.get("title")) or title, clean_text(data.get("summary")) or summary
    except Exception as e:
        print("Gemini translation skipped:", e)
        return title, summary


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
                ko_title, ko_summary = translate_ko(title, summary)
                out.append({
                    "id": make_id(url), "type": "news", "brand": brand,
                    "source": src["name"], "title": ko_title,
                    "summary": ko_summary, "url": url,
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
                if not any(k in (title + " " + context).lower() for k in ["news", "release", "lens", "camera", "product", "発売", "発表", "新製品", "レンズ"]):
                    continue
                ko_title, ko_summary = translate_ko(title, context)
                out.append({
                    "id": make_id(href), "type": "news", "brand": src["brand"],
                    "source": src["name"], "title": ko_title,
                    "summary": ko_summary or "공식 홈페이지에서 자세한 내용을 확인하세요.",
                    "url": href, "published_at": datetime.now(KST).isoformat(),
                })
                if len(seen) >= 18:
                    break
        except Exception as e:
            print(f"Official page failed: {src['name']}: {e}")
    return out


def collect_youtube() -> list[dict]:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return []
    out = []
    for brand, query in YOUTUBE_QUERIES.items():
        try:
            params = {
                "part": "snippet", "type": "video", "maxResults": 5,
                "order": "date", "q": query, "relevanceLanguage": "ko", "regionCode": "KR", "key": key,
            }
            data = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=TIMEOUT).json()
            for item in data.get("items", []):
                vid = item.get("id", {}).get("videoId")
                snip = item.get("snippet", {})
                if not vid:
                    continue
                url = f"https://www.youtube.com/watch?v={vid}"
                out.append({
                    "id": make_id(url), "type": "video", "brand": brand,
                    "source": snip.get("channelTitle") or "YouTube",
                    "title": clean_text(snip.get("title")),
                    "summary": clean_text(snip.get("description")),
                    "url": url, "published_at": parse_date(snip.get("publishedAt")),
                })
        except Exception as e:
            print(f"YouTube failed: {brand}: {e}")
    return out


def load_existing() -> list[dict]:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8")).get("items", [])
    except Exception:
        return []


def main():
    existing = [x for x in load_existing() if not str(x.get("id", "")).startswith("welcome-")]
    items = existing + collect_rss() + collect_official_pages() + collect_youtube()
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
