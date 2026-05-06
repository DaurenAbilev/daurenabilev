from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
AUTH_FILE = BASE_DIR / "auth_data.json"

load_dotenv(ENV_FILE)


@dataclass(slots=True)
class Settings:
    base_url: str = os.getenv("BASE_URL", "https://inforyou.teamsystem.com/ssdunime")
    company_id: int = int(os.getenv("COMPANY_ID", "2"))
    app_token: str = os.getenv("APP_TOKEN", "")
    iyes_url: str = os.getenv("IYES_URL", "http://192.167.102.90:65432/")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    default_login: str = os.getenv("UNIME_LOGIN", "")
    default_password: str = os.getenv("UNIME_PASSWORD", "")
    target_service: str = os.getenv(
        "TARGET_SERVICE",
        "SALA PESI PAL. MARIANI STUDENTI",
    )
    auth_file: Path = AUTH_FILE

    def validate(self) -> None:
        missing: list[str] = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.app_token:
            missing.append("APP_TOKEN")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")


settings = Settings()
