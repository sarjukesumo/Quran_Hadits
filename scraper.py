import json
import time
from datetime import datetime
from pathlib import Path

import requests

from config import Config
from utils import setup_logger


class QuranScraper:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger("scraper", config.LOG_DIR, config.LOG_LEVEL)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TuyulDatasetBot/1.0"})

    def _request(self, url: str) -> dict | None:
        for attempt in range(self.config.MAX_RETRIES):
            try:
                resp = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{self.config.MAX_RETRIES} failed: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        return None

    def get_surah_list(self) -> list[dict]:
        url = f"{self.config.QURAN_API_BASE}/surah"
        data = self._request(url)
        if data and data.get("code") == 200:
            return data["data"]
        self.logger.error("Failed to fetch surah list")
        return []

    def get_surah_with_translations(self, surah_number: int) -> dict | None:
        editions = ",".join(self.config.QURAN_EDITIONS.values())
        url = f"{self.config.QURAN_API_BASE}/surah/{surah_number}/editions/{editions}"
        data = self._request(url)

        if not data or data.get("code") != 200:
            self.logger.error(f"Failed to fetch surah {surah_number}")
            return None

        editions_data = data.get("data", [])
        expected = len(self.config.QURAN_EDITIONS)
        if not editions_data or len(editions_data) < expected:
            self.logger.warning(f"Surah {surah_number}: got {len(editions_data)} editions, expected {expected}")
            return None

        edition_maps = []
        for ed in editions_data:
            edition_maps.append({a["numberInSurah"]: a for a in ed.get("ayahs", [])})

        surah_info = editions_data[0]
        verses = []
        all_verse_nums = sorted(edition_maps[0].keys())

        for vn in all_verse_nums:
            verse = {
                "surah_number": surah_info["number"],
                "surah_name_arabic": surah_info["name"],
                "surah_name_english": surah_info.get("englishName", ""),
                "surah_name_translation": surah_info.get("englishNameTranslation", ""),
                "verse_number": vn,
                "verse_arabic": "",
                "verse_english": "",
                "verse_indonesian": "",
                "juz_number": 0,
                "page_number": 0,
            }

            for i, lang in enumerate(self.config.QURAN_EDITIONS):
                if i < len(edition_maps) and vn in edition_maps[i]:
                    ayah = edition_maps[i][vn]
                    verse[f"verse_{lang}"] = ayah.get("text", "")
                    if "juz" in ayah:
                        verse["juz_number"] = ayah["juz"]
                    if "page" in ayah:
                        verse["page_number"] = ayah["page"]

            verses.append(verse)

        return {"surah": surah_info, "verses": verses, "total_verses": len(verses)}

    def fetch_all(self) -> list[dict]:
        self.logger.info("Starting Quran data fetch ...")
        surah_list = self.get_surah_list()
        if not surah_list:
            return []

        self.logger.info(f"Found {len(surah_list)} surahs")
        all_data = []

        for i, surah in enumerate(surah_list, 1):
            sn = surah["number"]
            name = surah.get("englishName", "")
            self.logger.info(f"[{i}/{len(surah_list)}] Surah {sn} – {name}")

            result = self.get_surah_with_translations(sn)
            if result:
                all_data.append(result)
                self.logger.info(f"  + {result['total_verses']} verses")
            else:
                self.logger.warning(f"  - failed, skipping")

            time.sleep(self.config.REQUEST_DELAY)

        self.logger.info(f"Done: {len(all_data)}/{len(surah_list)} surahs fetched")
        return all_data

    def save_raw(self, data: list[dict], filename: str | None = None):
        if not filename:
            filename = f"quran_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        raw_dir = self.config.RAW_DIR / "quran"
        raw_dir.mkdir(parents=True, exist_ok=True)
        path = raw_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Raw data saved: {path} ({len(data)} surahs)")
        return path
