import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    RAW_DIR = DATA_DIR / "raw"
    PROCESSED_DIR = DATA_DIR / "processed"
    OUTPUT_DIR = BASE_DIR / "output"
    LOG_DIR = BASE_DIR / "logs"

    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

    QURAN_API_BASE = "https://api.alquran.cloud/v1"
    QURAN_EDITIONS = {
        "arabic": "quran-uthmani",
        "english": "en.sahih",
        "indonesian": "id.indonesian",
    }

    HF_TOKEN = os.getenv("HF_TOKEN", "")
    HF_USERNAME = os.getenv("HF_USERNAME", "")

    @property
    def hf_configured(self) -> bool:
        return bool(self.HF_TOKEN) and bool(self.HF_USERNAME)

    RUN_INTERVAL_HOURS = int(os.getenv("RUN_INTERVAL", "168"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
