from __future__ import annotations

import pytest

from stock_agent_arbiter.config import ConfigurationError, Settings


def test_settings_from_env_reads_required_values(tmp_path) -> None:
    settings = Settings.from_env(
        {
            "DTRADER_BASE_URL": "https://v3.example",
            "DTRADER_AUTH": "secret",
            "OPENAI_API_KEY": "openai",
            "OPENAI_MODEL": "model",
            "OPENAI_BASE_URL": "https://llm.example/v1",
            "STOCK_AGENT_OUTPUT_DIR": str(tmp_path),
        }
    )

    assert settings.dtrader_base_url == "https://v3.example"
    assert settings.dtrader_auth == "secret"
    assert settings.openai_api_key == "openai"
    assert settings.openai_model == "model"
    assert settings.openai_base_url == "https://llm.example/v1"
    assert settings.output_dir == tmp_path


def test_settings_from_env_reports_missing_variables() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        Settings.from_env({})

    message = str(exc_info.value)
    assert "DTRADER_BASE_URL" in message
    assert "DTRADER_AUTH" in message
    assert "OPENAI_API_KEY" in message
    assert "OPENAI_MODEL" in message
