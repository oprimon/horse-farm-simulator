"""Runtime entry point for Pferdehof Sim Discord Bot."""

import asyncio

from pferdehof_bot.bot import create_bot, load_extensions
from pferdehof_bot.config import ConfigError, load_config


def main() -> None:
    """Create and run the Discord bot."""
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return

    bot = create_bot()
    asyncio.run(load_extensions(bot))
    bot.run(config.token)


if __name__ == "__main__":
    main()
