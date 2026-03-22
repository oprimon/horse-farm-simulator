"""Runtime configuration for the Pferdehof bot."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class BotConfig:
    """Configuration values required to start the bot."""

    token: str


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def load_config() -> BotConfig:
    """Load bot configuration from environment variables."""
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ConfigError("DISCORD_TOKEN is not set.")
    return BotConfig(token=token)
