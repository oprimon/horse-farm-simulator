"""Tests for bot factory setup."""

from pferdehof_bot.bot import create_bot


def test_create_bot_uses_default_prefix():
    bot = create_bot()

    assert bot.command_prefix == "!"


def test_create_bot_accepts_custom_prefix():
    bot = create_bot(command_prefix="/")

    assert bot.command_prefix == "/"
