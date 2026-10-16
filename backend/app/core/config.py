from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project ka main folder (root directory) set kar rahe hain
BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # .env file mein DATABASE_URL naam ka variable hona zaroori hai
    database_url: str

    # Configuration: .env file kahan hai aur use kaise read karna hai
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",   # .env file ka exact path
        env_file_encoding="utf-8",    # Text format
        extra="ignore",               # Agar .env me extra variables hain, toh unpar error mat do
    )

# Is object ko banate hi .env ka data load ho jayega.
# Phir hum pure project me 'settings.database_url' likh kar URL fetch kar sakte hain.
settings = Settings()