from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PERFIN_PASSPHRASE: str = "change-me"
    PERFIN_SESSION_SECRET: str = "dev-secret-please-change"
    PERFIN_DB_PATH: Path = Path("./perfin.db")
    PERFIN_PORT: int = 8787
    TAILSCALE_BIND: bool = True

    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"
    CLAUDE_MODEL_HEAVY: str = "claude-sonnet-4-6"
    MAX_MONTHLY_TOKENS: int = 500_000

    AGENTMAIL_API_KEY: str = ""
    AGENTMAIL_INBOX_ID: str = ""
    AGENTMAIL_SUBJECT_FILTER: str = "JY Statement"
    AGENTMAIL_POLL_CRON: str = "0 7 * * *"
    AGENTMAIL_SENDER_PASSWORDS_JSON: str = "{}"

    @field_validator("PERFIN_DB_PATH", mode="before")
    @classmethod
    def _coerce_path(cls, v):
        return Path(v) if not isinstance(v, Path) else v

    @property
    def agentmail_sender_passwords(self) -> dict[str, str]:
        try:
            return json.loads(self.AGENTMAIL_SENDER_PASSWORDS_JSON or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def agentmail_enabled(self) -> bool:
        return bool(self.AGENTMAIL_API_KEY and self.AGENTMAIL_INBOX_ID)


@lru_cache
def get_settings() -> Settings:
    return Settings()
