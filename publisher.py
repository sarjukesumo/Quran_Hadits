from datetime import datetime
from pathlib import Path

from huggingface_hub import HfApi, login

from config import Config
from utils import setup_logger

DATASET_CARD = """---
license: mit
language:
- ar
- en
- id
pretty_name: Quran Parallel Corpus
task_categories:
- translation
- text-generation
- fill-mask
tags:
- quran
- islamic
- parallel-corpus
- arabic
- indonesian
size_categories:
- 10K<n<100K
---

# Quran Parallel Corpus

Verse-aligned Quran parallel corpus — Arabic (Uthmani), English (Sahih International), and Indonesian (Ministry of Religious Affairs).

## Stats
- **Total verses:** {total_verses}
- **Languages:** Arabic, English, Indonesian
- **Translation pairs:** Arabic↔English, Arabic↔Indonesian, English↔Indonesian
- **Formats:** JSONL, CSV, Parquet

## Structure
Each verse record contains:
| Field | Description |
|-------|-------------|
| `surah_number` | Chapter (1–114) |
| `surah_name_arabic` | Arabic surah name |
| `surah_name_english` | English transliteration |
| `verse_number` | Verse within surah |
| `verse_arabic` | Uthmani script |
| `verse_english` | Sahih International translation |
| `verse_indonesian` | Indonesian Ministry translation |
| `juz_number` | Juz/part number |
| `page_number` | Page in standard print |

## Usage
```python
from datasets import load_dataset
ds = load_dataset("{hf_username}/quran-parallel-corpus", split="train")
```

## Applications
- Machine translation (Arabic ↔ English / Indonesian)
- Cross-lingual NLP
- Islamic AI assistants & education

## License
📌 **Free for research & educational use** under MIT.
🚀 **Commercial use requires a license.** Contact for pricing.

| Use Case | License |
|----------|---------|
| Research, thesis, education | ✅ Free (MIT) |
| Open-source project | ✅ Free (MIT) |
| Startup / MVP (revenue < $50k/yr) | 💰 $50 one-time |
| Company / Production API | 💰 $200–$500 /yr |
| AI model training (commercial) | 💰 $500–$2,000 |
| Custom dataset / white-label | 💰 Negotiable |

**Contact:** [Open an issue](https://github.com/{hf_username}/quran-parallel-corpus/issues) or email.

## Citation
```
@misc{{quran-parallel-corpus-{year},
  author = {{{author}}},
  title = {{Quran Parallel Corpus}},
  year = {{{year}}},
  publisher = {{Hugging Face}},
  url = {{https://huggingface.co/datasets/{hf_username}/quran-parallel-corpus}}
}}
```
"""


class HuggingFacePublisher:
    DATASET_ID = "quran-parallel-corpus"

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger("publisher", config.LOG_DIR, config.LOG_LEVEL)
        self.api = HfApi()

    def login(self) -> bool:
        if not self.config.hf_configured:
            self.logger.warning("HF_TOKEN or HF_USERNAME not set — skipping")
            return False
        try:
            login(token=self.config.HF_TOKEN, add_to_git_credential=False)
            self.logger.info("Logged in to Hugging Face")
            return True
        except Exception as e:
            self.logger.error(f"HF login failed: {e}")
            return False

    def create_or_update_repo(self) -> bool:
        repo_id = f"{self.config.HF_USERNAME}/{self.DATASET_ID}"
        try:
            self.api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)
            self.logger.info(f"Repo ready: {repo_id}")
            return True
        except Exception as e:
            self.logger.error(f"Repo create/update failed: {e}")
            return False

    def upload_files(self, dataset_paths: dict):
        repo_id = f"{self.config.HF_USERNAME}/{self.DATASET_ID}"
        for _, path in dataset_paths.items():
            p = Path(path)
            if not p.exists():
                continue
            for fpath in p.iterdir():
                if not fpath.is_file():
                    continue
                hf_path = f"data/{fpath.name}"
                try:
                    self.api.upload_file(
                        path_or_fileobj=str(fpath),
                        path_in_repo=hf_path,
                        repo_id=repo_id,
                        repo_type="dataset",
                    )
                    self.logger.info(f"  Uploaded: {hf_path}")
                except Exception as e:
                    self.logger.error(f"  Upload failed: {fpath.name} – {e}")

    def set_dataset_id(self, dataset_id: str):
        self.DATASET_ID = dataset_id

    def upload_dataset_card(self, total_verses: int):
        repo_id = f"{self.config.HF_USERNAME}/{self.DATASET_ID}"
        card = DATASET_CARD.format(
            total_verses=total_verses,
            hf_username=self.config.HF_USERNAME,
            author=self.config.HF_USERNAME,
            year=datetime.now().year,
        )
        try:
            self.api.upload_file(
                path_or_fileobj=card.encode("utf-8"),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
            )
            self.logger.info("  Dataset card (README.md) uploaded")
        except Exception as e:
            self.logger.error(f"Card upload failed: {e}")

    def publish(self, verses: list[dict], dataset_paths: dict) -> bool:
        self.logger.info("--- Publishing to Hugging Face ---")
        if not self.login():
            return False
        if not self.create_or_update_repo():
            return False

        self.upload_files(dataset_paths)
        self.upload_dataset_card(len(verses))

        url = f"https://huggingface.co/datasets/{self.config.HF_USERNAME}/{self.DATASET_ID}"
        self.logger.info(f"Published: {url}")
        return True

    def publish_hadith(self, hadiths: list[dict], dataset_paths: dict) -> bool:
        self.set_dataset_id("hadith-parallel-corpus")
        self.logger.info("--- Publishing Hadith dataset to Hugging Face ---")

        if not self.login():
            return False
        if not self.create_or_update_repo():
            return False

        self.upload_files(dataset_paths)
        self._upload_hadith_card(len(hadiths))

        url = f"https://huggingface.co/datasets/{self.config.HF_USERNAME}/{self.DATASET_ID}"
        self.logger.info(f"Published: {url}")
        return True

    def _upload_hadith_card(self, total_hadith: int):
        repo_id = f"{self.config.HF_USERNAME}/{self.DATASET_ID}"
        card = f"""---
license: mit
language:
- ar
- en
- id
pretty_name: Hadith Parallel Corpus
task_categories:
- translation
- text-generation
- question-answering
tags:
- hadith
- islamic
- parallel-corpus
- arabic
- prophet
- sunnah
size_categories:
- 100K<n<1M
---

# Hadith Parallel Corpus

Aligned Hadith corpus from the 7 major collections — Arabic + English + Indonesian.

## Collections included
| # | Collection | Hadith |
|---|------------|-------:|
| 1 | Sahih al-Bukhari | 7,589 |
| 2 | Sahih Muslim | 5,700+ |
| 3 | Sunan Abu Dawud | 5,274 |
| 4 | Jami At Tirmidhi | 3,956 |
| 5 | Sunan an Nasai | 5,761 |
| 6 | Sunan Ibn Majah | 4,341 |
| 7 | Muwatta Malik | 1,720 |

## Stats
- **Total hadith entries:** {total_hadith}
- **Languages:** Arabic, English, Indonesian
- **Translation pairs:** Arabic↔English, Arabic↔Indonesian, English↔Indonesian
- **Formats:** JSONL, CSV, Parquet
- **Source:** [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) (CDN)

## Structure
Each hadith record contains:
| Field | Description |
|-------|-------------|
| `collection` | Book name (e.g. Sahih al-Bukhari) |
| `hadith_number` | Hadith number in collection |
| `arabic_number` | Arabic reference number |
| `book_number` | Book number within collection |
| `hadith_arabic` | Arabic text |
| `hadith_english` | English translation |
| `hadith_indonesian` | Indonesian translation |
| `grades` | Authenticity grades |

## Usage
```python
from datasets import load_dataset
ds = load_dataset("{hf_username}/hadith-parallel-corpus", split="train")
```

## License
📌 **Free for research & educational use** under MIT.
🚀 **Commercial use requires a license.** Contact for pricing.

| Use Case | License |
|----------|---------|
| Research, thesis, education | ✅ Free (MIT) |
| Open-source project | ✅ Free (MIT) |
| Startup / MVP (revenue < $50k/yr) | 💰 $50 one-time |
| Company / Production API | 💰 $200–$500 /yr |
| AI model training (commercial) | 💰 $500–$2,000 |
| Custom dataset / white-label | 💰 Negotiable |

**Contact:** [Open an issue](https://github.com/{hf_username}/hadith-parallel-corpus/issues) or email.

## Citation
```
@misc{{hadith-parallel-corpus-{year},
  author = {{{author}}},
  title = {{Hadith Parallel Corpus}},
  year = {{{year}}},
  publisher = {{Hugging Face}},
  url = {{https://huggingface.co/datasets/{hf_username}/hadith-parallel-corpus}}
}}
```
"""
        try:
            self.api.upload_file(
                path_or_fileobj=card.encode("utf-8"),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
            )
            self.logger.info("  Hadith dataset card (README.md) uploaded")
        except Exception as e:
            self.logger.error(f"Card upload failed: {e}")
