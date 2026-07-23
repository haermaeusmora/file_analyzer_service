import os
from pathlib import Path

class Settings:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    DATA_DIR = os.getenv("DATA_DIR", str(Path(__file__).resolve().parent.parent / "data"))
    PORT = int(os.getenv("PORT", 8001))
    HOST = os.getenv("HOST", "0.0.0.0")

settings = Settings()