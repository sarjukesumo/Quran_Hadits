#!/usr/bin/env python3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import schedule as sched

from config import Config
from utils import setup_logger, ensure_dirs
from scraper import QuranScraper
from hadith_scraper import HadithScraper
from processor import DataProcessor
from publisher import HuggingFacePublisher


def run_quran_pipeline(config: Config):
    log = setup_logger("pipeline", config.LOG_DIR, config.LOG_LEVEL)
    log.info("  === QURAN PIPELINE ===")

    try:
        log.info("Phase 1/3: Scraping Quran data")
        scraper = QuranScraper(config)
        raw = scraper.fetch_all()
        if not raw:
            log.error("No Quran data scraped — aborting")
            return
        scraper.save_raw(raw)

        log.info("Phase 2/3: Processing & cleaning")
        proc = DataProcessor(config)
        verses = proc.build_verses_dataset(raw)
        pairs = proc.build_translation_pairs(verses)
        paths = proc.save_all(verses, pairs)

        if config.hf_configured:
            log.info("Phase 3/3: Publishing Quran to Hugging Face")
            pub = HuggingFacePublisher(config)
            ok = pub.publish(verses, paths)
            log.info(f"  Quran publish {'OK' if ok else 'FAILED'}")
        else:
            log.warning("HF_TOKEN not set — saving locally only")

        log.info("  === QURAN DONE ===")

    except Exception as e:
        log.error(f"Quran pipeline crashed: {e}", exc_info=True)


def run_hadith_pipeline(config: Config):
    log = setup_logger("pipeline", config.LOG_DIR, config.LOG_LEVEL)
    log.info("  === HADITH PIPELINE ===")

    try:
        log.info("Phase 1/3: Scraping Hadith data")
        scraper = HadithScraper(config)
        raw = scraper.fetch_all()
        if not raw:
            log.warning("No hadith data scraped — skipping hadith")
            return
        scraper.save_raw(raw)

        log.info("Phase 2/3: Processing & cleaning")
        proc = DataProcessor(config)
        hadiths = proc.build_hadith_dataset(raw)
        pairs = proc.build_hadith_translation_pairs(hadiths)
        paths = proc.save_hadith_datasets(hadiths, pairs)

        if config.hf_configured:
            log.info("Phase 3/3: Publishing Hadith to Hugging Face")
            pub = HuggingFacePublisher(config)
            ok = pub.publish_hadith(hadiths, paths)
            log.info(f"  Hadith publish {'OK' if ok else 'FAILED'}")
        else:
            log.warning("HF_TOKEN not set — saving locally only")

        log.info("  === HADITH DONE ===")

    except Exception as e:
        log.error(f"Hadith pipeline crashed: {e}", exc_info=True)


def run_pipeline(config: Config):
    log = setup_logger("pipeline", config.LOG_DIR, config.LOG_LEVEL)
    log.info("=" * 55)
    log.info("  FULL PIPELINE STARTED")
    log.info("=" * 55)

    run_quran_pipeline(config)
    run_hadith_pipeline(config)

    log.info("=" * 55)
    log.info("  FULL PIPELINE COMPLETED")
    log.info("=" * 55)


def main():
    config = Config()
    ensure_dirs([config.DATA_DIR, config.RAW_DIR, config.PROCESSED_DIR, config.OUTPUT_DIR, config.LOG_DIR])

    log = setup_logger("bot", config.LOG_DIR, config.LOG_LEVEL)
    log.info("Tuyul Dataset Bot v1.0")
    log.info(f"Schedule: every {config.RUN_INTERVAL_HOURS}h")
    log.info(f"HF ready: {config.hf_configured}")

    run_pipeline(config)

    sched.every(config.RUN_INTERVAL_HOURS).hours.do(run_pipeline, config)
    log.info(f"Next run in {config.RUN_INTERVAL_HOURS}h — sleeping")

    while True:
        sched.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
