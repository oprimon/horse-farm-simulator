"""Tests for runtime configuration loading."""

from pferdehof_bot.config import ConfigError, load_config


def test_load_config_reads_token(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")

    config = load_config()

    assert config.token == "test-token"


def test_load_config_raises_when_missing_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)

    try:
        load_config()
        did_raise = False
    except ConfigError:
        did_raise = True

    assert did_raise is True


def test_load_config_reads_token_from_dotenv(monkeypatch, tmp_path):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DISCORD_TOKEN=dotenv-token\n", encoding="utf-8")

    config = load_config()

    assert config.token == "dotenv-token"


def test_load_config_prefers_environment_over_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DISCORD_TOKEN=dotenv-token\n", encoding="utf-8")
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")

    config = load_config()

    assert config.token == "env-token"
