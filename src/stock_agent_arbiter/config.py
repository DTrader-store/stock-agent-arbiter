from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator


class ConfigurationError(RuntimeError):
    """Raised when runtime configuration is missing or invalid."""


class Settings(BaseModel):
    dtrader_base_url: str = Field(min_length=1)
    dtrader_auth: str = Field(min_length=1)
    openai_api_key: str = Field(min_length=1)
    openai_model: str = Field(min_length=1)
    openai_base_url: str | None = None
    output_dir: Path = Path("reports")

    @field_validator("dtrader_base_url", "dtrader_auth", "openai_api_key", "openai_model", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("openai_base_url", mode="before")
    @classmethod
    def normalize_optional(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        if env is None:
            load_dotenv()
            env = os.environ

        raw = {
            "dtrader_base_url": env.get("DTRADER_BASE_URL"),
            "dtrader_auth": env.get("DTRADER_AUTH"),
            "openai_api_key": env.get("OPENAI_API_KEY"),
            "openai_model": env.get("OPENAI_MODEL"),
            "openai_base_url": env.get("OPENAI_BASE_URL"),
            "output_dir": env.get("STOCK_AGENT_OUTPUT_DIR") or "reports",
        }
        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            missing = [
                env_name
                for field, env_name in {
                    "dtrader_base_url": "DTRADER_BASE_URL",
                    "dtrader_auth": "DTRADER_AUTH",
                    "openai_api_key": "OPENAI_API_KEY",
                    "openai_model": "OPENAI_MODEL",
                }.items()
                if not raw.get(field)
            ]
            if missing:
                raise ConfigurationError(f"Missing required environment variables: {', '.join(missing)}") from exc
            raise ConfigurationError(str(exc)) from exc


def create_chat_model(settings: Settings):
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, object] = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.2,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def create_dtrader_client(settings: Settings):
    from dtrader_v3_sdk import DTraderClient

    return DTraderClient(base_url=settings.dtrader_base_url, auth=settings.dtrader_auth)
