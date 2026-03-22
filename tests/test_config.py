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
