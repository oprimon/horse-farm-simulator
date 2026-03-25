"""Tests for runtime configuration loading."""

from pathlib import Path

import pferdehof_bot.config as config_module
from pferdehof_bot.config import ConfigError, load_config


def test_load_config_reads_token(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.delenv("DISCORD_COMMAND_SYNC", raising=False)
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)

    config = load_config()

    assert config.token == "test-token"
    assert config.command_sync_mode == "global"
    assert config.command_sync_dev_guild_id is None


def test_load_config_raises_when_missing_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_COMMAND_SYNC", raising=False)
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)
    monkeypatch.setattr(config_module, "_resolve_dotenv_path", lambda: "")

    try:
        load_config()
        did_raise = False
    except ConfigError:
        did_raise = True

    assert did_raise is True


def test_load_config_reads_token_from_dotenv(monkeypatch, tmp_path):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_COMMAND_SYNC", raising=False)
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DISCORD_TOKEN=dotenv-token\n", encoding="utf-8")

    config = load_config()

    assert config.token == "dotenv-token"


def test_load_config_prefers_environment_over_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DISCORD_TOKEN=dotenv-token\n", encoding="utf-8")
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")
    monkeypatch.delenv("DISCORD_COMMAND_SYNC", raising=False)
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)

    config = load_config()

    assert config.token == "env-token"


def test_load_config_reads_token_from_script_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_COMMAND_SYNC", raising=False)
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)
    launch_dir = tmp_path / "deploy"
    launch_dir.mkdir()
    (launch_dir / ".env").write_text("DISCORD_TOKEN=script-token\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", [str(launch_dir / "main.py")])

    config = load_config()

    assert config.token == "script-token"


def test_load_config_accepts_global_command_sync(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("DISCORD_COMMAND_SYNC", "global")
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)

    config = load_config()

    assert config.command_sync_mode == "global"
    assert config.command_sync_dev_guild_id is None


def test_load_config_accepts_auto_command_sync(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("DISCORD_COMMAND_SYNC", "auto")
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)

    config = load_config()

    assert config.command_sync_mode == "auto"
    assert config.command_sync_dev_guild_id is None


def test_load_config_requires_dev_guild_for_guild_sync(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("DISCORD_COMMAND_SYNC", "guild")
    monkeypatch.delenv("DISCORD_DEV_GUILD_ID", raising=False)

    try:
        load_config()
        did_raise = False
    except ConfigError:
        did_raise = True

    assert did_raise is True


def test_load_config_parses_dev_guild_id(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("DISCORD_COMMAND_SYNC", "guild")
    monkeypatch.setenv("DISCORD_DEV_GUILD_ID", "123456")

    config = load_config()

    assert config.command_sync_mode == "guild"
    assert config.command_sync_dev_guild_id == 123456
