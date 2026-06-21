import json
from datetime import datetime
from pathlib import Path

import requests

from config import Config
from utils import setup_logger

CDN_BASE = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1"

MAIN_BOOKS = {
    "bukhari": "Sahih al-Bukhari",
    "muslim": "Sahih Muslim",
    "abudawud": "Sunan Abu Dawud",
    "tirmidhi": "Jami At Tirmidhi",
    "nasai": "Sunan an Nasai",
    "ibnmajah": "Sunan Ibn Majah",
    "malik": "Muwatta Malik",
}

TARGET_LANGS = ["ara", "eng", "ind"]


class HadithScraper:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger("hadith-scraper", config.LOG_DIR, config.LOG_LEVEL)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TuyulDatasetBot/1.0"})

    def _request(self, url: str) -> dict | None:
        for attempt in range(self.config.MAX_RETRIES):
            try:
                resp = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    import time
                    time.sleep(2 ** attempt)
        return None

    def get_editions_map(self) -> dict:
        url = f"{CDN_BASE}/editions.min.json"
        data = self._request(url)
        if not data:
            return {}

        editions_map = {}
        for book_slug in MAIN_BOOKS:
            if book_slug not in data:
                continue
            langs = {}
            for edition in data[book_slug]["collection"]:
                for prefix in TARGET_LANGS:
                    if edition["name"].startswith(f"{prefix}-{book_slug}"):
                        langs[prefix] = {
                            "name": edition["name"],
                            "url": edition["linkmin"],
                        }
            if langs:
                editions_map[book_slug] = {
                    "title": MAIN_BOOKS[book_slug],
                    "langs": langs,
                }

        self.logger.info(f"Found {len(editions_map)} books with target languages")
        return editions_map

    def download_edition(self, url: str, label: str) -> list[dict] | None:
        self.logger.info(f"  Downloading {label} ...")
        data = self._request(url)
        if not data or "hadiths" not in data:
            self.logger.warning(f"  Empty or invalid: {label}")
            return None
        self.logger.info(f"  Got {len(data['hadiths'])} hadith from {label}")
        return data["hadiths"]

    def align_hadith(
        self,
        arabic: list[dict],
        english: list[dict],
        indonesian: list[dict] | None,
    ) -> list[dict]:
        def build_index(hadith_list):
            idx = {}
            for h in hadith_list:
                key = (h.get("hadithnumber"), h.get("arabicnumber"))
                idx[key] = h
                idx[h.get("hadithnumber")] = h  # fallback by hadithnumber only
            return idx

        ar_idx = build_index(arabic) if arabic else {}
        en_idx = build_index(english) if english else {}
        id_idx = build_index(indonesian) if indonesian else {}

        # Align by using English list as reference (most complete)
        aligned = []
        ref_hadiths = english or arabic or indonesian or []

        for h in ref_hadiths:
            hn = h.get("hadithnumber")
            an = h.get("arabicnumber")

            def find(idx, hn, an):
                if (hn, an) in idx:
                    return idx[(hn, an)]
                if hn in idx:
                    return idx[hn]
                return None

            ar = find(ar_idx, hn, an)
            en = find(en_idx, hn, an)
            id_ = find(id_idx, hn, an)

            if not ar and not en:
                continue

            entry = {
                "collection": "",
                "hadith_number": hn,
                "arabic_number": str(an) if an is not None else "",
                "book_number": None,
                "chapter_number": None,
                "chapter_title": "",
                "hadith_arabic": (ar or {}).get("text", "") if ar else "",
                "hadith_english": (en or {}).get("text", "") if en else "",
                "hadith_indonesian": (id_ or {}).get("text", "") if id_ else "",
                "grades": (en or ar or {}).get("grades", []),
                "reference_book": None,
                "reference_hadith": None,
            }

            ref = (en or ar or {}).get("reference", {})
            if ref:
                entry["book_number"] = ref.get("book")
                entry["reference_book"] = ref.get("book")
                entry["reference_hadith"] = ref.get("hadith")

            aligned.append(entry)

        return aligned

    def fetch_book(self, book_slug: str, book_info: dict) -> list[dict] | None:
        self.logger.info(f"=== {book_info['title']} ===")

        langs = book_info["langs"]
        arabic = self.download_edition(langs.get("ara", {}).get("url", ""), "ara") if "ara" in langs else None
        english = self.download_edition(langs.get("eng", {}).get("url", ""), "eng") if "eng" in langs else None
        indonesian = self.download_edition(langs.get("ind", {}).get("url", ""), "ind") if "ind" in langs else None

        if not arabic and not english:
            self.logger.warning(f"  No Arabic or English data for {book_slug}, skipping")
            return None

        aligned = self.align_hadith(arabic, english, indonesian)
        for entry in aligned:
            entry["collection"] = book_info["title"]

        self.logger.info(f"  Aligned: {len(aligned)} hadith")
        return aligned

    def fetch_all(self) -> dict[str, list[dict]]:
        self.logger.info("Starting Hadith data fetch ...")
        editions_map = self.get_editions_map()
        if not editions_map:
            self.logger.error("No editions found")
            return {}

        result = {}
        for book_slug, book_info in editions_map.items():
            aligned = self.fetch_book(book_slug, book_info)
            if aligned:
                result[book_slug] = aligned

        total = sum(len(v) for v in result.values())
        self.logger.info(f"Done: {len(result)} books, {total} total hadith aligned")
        return result

    def save_raw(self, data: dict[str, list[dict]], filename: str | None = None):
        if not filename:
            filename = f"hadith_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        raw_dir = self.config.RAW_DIR / "hadith"
        raw_dir.mkdir(parents=True, exist_ok=True)
        path = raw_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Raw data saved: {path} ({len(data)} books)")
        return path

    def save_raw_book(self, book_slug: str, aligned: list[dict]):
        raw_dir = self.config.RAW_DIR / "hadith"
        raw_dir.mkdir(parents=True, exist_ok=True)
        path = raw_dir / f"{book_slug}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(aligned, f, ensure_ascii=False, indent=2)
        return path
