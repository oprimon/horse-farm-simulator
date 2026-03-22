"""Runtime configuration for the Pferdehof bot."""

from dataclasses import dataclass
import os

from dotenv import find_dotenv, load_dotenv


@dataclass(frozen=True)
class BotConfig:
    """Configuration values required to start the bot."""

    token: str


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def load_config() -> BotConfig:
    """Load bot configuration from environment variables.

    A local `.env` file is loaded first to support local development.
    Existing process environment variables keep precedence.
    """
    dotenv_path = find_dotenv(usecwd=True)
    load_dotenv(dotenv_path=dotenv_path, override=False)
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ConfigError("DISCORD_TOKEN is not set.")
    return BotConfig(token=token)
