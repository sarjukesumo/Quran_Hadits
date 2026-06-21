import csv
import json
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import Config
from utils import setup_logger


class DataProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger("processor", config.LOG_DIR, config.LOG_LEVEL)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFC", text)
        text = " ".join(text.split())
        return text.strip()

    def build_verses_dataset(self, raw_data: list[dict]) -> list[dict]:
        self.logger.info("Building verse-level parallel dataset ...")
        all_verses = []

        for surah_data in raw_data:
            if not surah_data:
                continue
            for verse in surah_data.get("verses", []):
                cleaned = {
                    k: self.clean_text(v) if isinstance(v, str) else v
                    for k, v in verse.items()
                }
                all_verses.append(cleaned)

        self.logger.info(f"Total verses: {len(all_verses)}")
        return all_verses

    def build_translation_pairs(self, verses: list[dict]) -> dict[str, list[dict]]:
        self.logger.info("Building translation pair datasets ...")
        pairs = {
            "arabic_english": [],
            "arabic_indonesian": [],
            "english_indonesian": [],
        }

        for v in verses:
            ar = v.get("verse_arabic", "")
            en = v.get("verse_english", "")
            id_ = v.get("verse_indonesian", "")

            def entry(src, tgt):
                return {
                    "surah_number": v["surah_number"],
                    "surah_name": v["surah_name_english"],
                    "verse_number": v["verse_number"],
                    "source": src,
                    "target": tgt,
                }

            if ar and en:
                pairs["arabic_english"].append(entry(ar, en))
            if ar and id_:
                pairs["arabic_indonesian"].append(entry(ar, id_))
            if en and id_:
                pairs["english_indonesian"].append(entry(en, id_))

        for name, data in pairs.items():
            self.logger.info(f"  {name}: {len(data)} pairs")
        return pairs

    def save_dataset(self, data: list[dict], name: str) -> Path:
        out_dir = self.config.OUTPUT_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d")

        jsonl_path = out_dir / f"{name}_{ts}.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.logger.info(f"JSONL: {jsonl_path} ({len(data)} rows)")

        csv_path = out_dir / f"{name}_{ts}.csv"
        if data:
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
                w.writeheader()
                w.writerows(data)
        self.logger.info(f"CSV:  {csv_path}")

        try:
            parquet_path = out_dir / f"{name}_{ts}.parquet"
            pd.DataFrame(data).to_parquet(parquet_path, index=False)
            self.logger.info(f"Parquet: {parquet_path}")
        except Exception as e:
            self.logger.warning(f"Parquet skip: {e}")

        return out_dir

    # ---- Hadith processing ----

    def build_hadith_dataset(self, raw_books: dict[str, list[dict]]) -> list[dict]:
        self.logger.info("Building hadith parallel dataset ...")
        all_hadith = []
        for book_slug, hadith_list in raw_books.items():
            for h in hadith_list:
                cleaned = {}
                for k, v in h.items():
                    if isinstance(v, str):
                        cleaned[k] = self.clean_text(v)
                    elif k == "arabic_number":
                        cleaned[k] = str(v) if v is not None else ""
                    elif isinstance(v, list):
                        cleaned[k] = [str(g) for g in v] if v else []
                    else:
                        cleaned[k] = v
                all_hadith.append(cleaned)
        self.logger.info(f"Total hadith entries: {len(all_hadith)}")
        return all_hadith

    def build_hadith_translation_pairs(self, hadiths: list[dict]) -> dict[str, list[dict]]:
        self.logger.info("Building hadith translation pairs ...")
        pairs = {"arabic_english": [], "arabic_indonesian": [], "english_indonesian": []}

        for h in hadiths:
            ar = h.get("hadith_arabic", "")
            en = h.get("hadith_english", "")
            id_ = h.get("hadith_indonesian", "")

            def entry(src, tgt):
                return {
                    "collection": h.get("collection", ""),
                    "hadith_number": h.get("hadith_number"),
                    "book_number": h.get("book_number"),
                    "source": src,
                    "target": tgt,
                }

            if ar and en:
                pairs["arabic_english"].append(entry(ar, en))
            if ar and id_:
                pairs["arabic_indonesian"].append(entry(ar, id_))
            if en and id_:
                pairs["english_indonesian"].append(entry(en, id_))

        for name, data in pairs.items():
            self.logger.info(f"  {name}: {len(data)} pairs")
        return pairs

    def save_hadith_datasets(self, hadiths: list[dict], pairs: dict) -> dict[str, Path]:
        self.logger.info("Saving hadith datasets ...")
        paths = {}
        paths["full"] = self.save_dataset(hadiths, "hadith_parallel_corpus")
        for pair_name, pair_data in pairs.items():
            paths[pair_name] = self.save_dataset(pair_data, f"hadith_{pair_name}")
        return paths

    def save_all(self, verses: list[dict], pairs: dict) -> dict[str, Path]:
        self.logger.info("Saving all datasets ...")
        paths = {}
        paths["full"] = self.save_dataset(verses, "quran_parallel_corpus")
        for pair_name, pair_data in pairs.items():
            paths[pair_name] = self.save_dataset(pair_data, f"quran_{pair_name}")
        return paths
