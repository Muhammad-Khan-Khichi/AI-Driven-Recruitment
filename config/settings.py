import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # AI
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = "mistral-tiny"
    TEMPERATURE = 0

    # Job APIs
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
    JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")

    # Search
    DEFAULT_LOCATION = "Lahore"
    DEFAULT_COUNTRY = "pk"
    MAX_JOBS_PER_QUERY = 15
    TOP_MATCHES_COUNT = 10

    # === HF Spaces: Use /tmp (only writable directory) ===
    OUTPUT_DIR = "/tmp/outputs"
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "results.json")
    COVER_LETTERS_DIR = os.environ.get("COVER_LETTERS_DIR", "/tmp/data/cover_letters")

    def __init__(self):
        # Create writable directories at startup
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.COVER_LETTERS_DIR, exist_ok=True)


settings = Settings()