"""Runtime configuration for the Pferdehof bot."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from dotenv import find_dotenv, load_dotenv


@dataclass(frozen=True)
class BotConfig:
    """Configuration values required to start the bot."""

    token: str
    command_sync_mode: str
    command_sync_dev_guild_id: int | None


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def _resolve_dotenv_path() -> str:
    """Locate a local `.env` file from common launch locations."""
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        return dotenv_path

    script_path = Path(sys.argv[0]).resolve()
    candidate_paths = (
        script_path.parent / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    )
    for candidate_path in candidate_paths:
        if candidate_path.is_file():
            return str(candidate_path)

    return ""


def load_config() -> BotConfig:
    """Load bot configuration from environment variables.

    A local `.env` file is loaded first to support local development.
    Existing process environment variables keep precedence.
    """
    dotenv_path = _resolve_dotenv_path()
    load_dotenv(dotenv_path=dotenv_path, override=False)
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ConfigError("DISCORD_TOKEN is not set.")

    sync_mode = os.getenv("DISCORD_COMMAND_SYNC", "global").strip().lower()
    if sync_mode not in {"off", "global", "guild", "auto"}:
        sync_mode = "global"

    dev_guild_raw = os.getenv("DISCORD_DEV_GUILD_ID", "").strip()
    if dev_guild_raw:
        try:
            dev_guild_id = int(dev_guild_raw)
        except ValueError as exc:
            raise ConfigError("DISCORD_DEV_GUILD_ID must be a numeric id.") from exc
    else:
        dev_guild_id = None

    if sync_mode == "guild" and dev_guild_id is None:
        raise ConfigError("DISCORD_DEV_GUILD_ID is required when DISCORD_COMMAND_SYNC=guild.")

    return BotConfig(
        token=token,
        command_sync_mode=sync_mode,
        command_sync_dev_guild_id=dev_guild_id,
    )
