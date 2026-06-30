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

    # Paths
    OUTPUT_FILE = "outputs/results.json"
    COVER_LETTERS_DIR = "data/cover_letters"


settings = Settings()