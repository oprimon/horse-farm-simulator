"""Runtime entry point for Pferdehof Sim Discord Bot."""

import asyncio

from pferdehof_bot.bot import CommandSyncSettings, create_bot, load_extensions
from pferdehof_bot.config import ConfigError, load_config


def main() -> None:
    """Create and run the Discord bot."""
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return

    bot = create_bot(
        command_sync_settings=CommandSyncSettings(
            mode=config.command_sync_mode,
            dev_guild_id=config.command_sync_dev_guild_id,
        )
    )
    asyncio.run(load_extensions(bot))
    bot.run(config.token)


if __name__ == "__main__":
    main()
