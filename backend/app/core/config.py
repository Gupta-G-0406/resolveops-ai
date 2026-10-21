from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project ka main folder (root directory) set kar rahe hain
BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # .env file mein DATABASE_URL naam ka variable hona zaroori hai
    database_url: str
    session_lifetime_hours: int = 24
    session_cookie_name: str = "resolveops_session"
    session_cookie_secure: bool = True
    login_rate_limit_secret: str
    login_rate_limit_window_minutes: int = 15
    login_rate_limit_client_max: int = 10
    login_rate_limit_account_max: int = 5
    auth_allowed_origins: list[str] = [
        "http://localhost:5173"
    ]

    # Configuration: .env file kahan hai aur use kaise read karna hai
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",   # .env file ka exact path
        env_file_encoding="utf-8",    # Text format
        extra="ignore",               # Agar .env me extra variables hain, toh unpar error mat do
    )

# Is object ko banate hi .env ka data load ho jayega.
# Phir hum pure project me 'settings.database_url' likh kar URL fetch kar sakte hain.
settings = Settings()