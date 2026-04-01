"""Shared response rendering helpers for slash-command handlers."""

from __future__ import annotations

import discord

from pferdehof_bot.command_registry import ResponseVisibility, get_command_metadata
from pferdehof_bot.services.presentation_models import ResponsePresentation


def build_embed(presentation: ResponsePresentation) -> discord.Embed:
    """Build a Discord embed from a service presentation payload."""
    accent = (presentation.accent or "").lower()
    color_by_accent: dict[str, discord.Color] = {
        "success": discord.Color.green(),
        "warning": discord.Color.orange(),
        "error": discord.Color.red(),
        "info": discord.Color.blurple(),
    }
    embed = discord.Embed(
        title=presentation.title,
        description=presentation.description,
        color=color_by_accent.get(accent, discord.Color.light_grey()),
    )
    for field in presentation.fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)
    if presentation.footer is not None:
        embed.set_footer(text=presentation.footer)
    return embed


async def send_response(
    *,
    interaction: discord.Interaction,
    command_id: str,
    message: str,
    presentation: ResponsePresentation | None = None,
    view: discord.ui.View | None = None,
    content_override: str | None = None,
    allowed_mentions: discord.AllowedMentions | None = None,
) -> None:
    """Send a response based on command visibility metadata."""
    metadata = get_command_metadata(command_id)
    is_ephemeral = metadata.visibility == ResponseVisibility.EPHEMERAL
    embed = build_embed(presentation) if presentation is not None else None
    content = message if content_override is None else content_override

    # When an embed is present, suppress plain-text content to avoid duplicate output.
    if embed is not None and view is not None:
        if allowed_mentions is not None:
            await interaction.response.send_message(
                content_override,
                embed=embed,
                view=view,
                ephemeral=is_ephemeral,
                allowed_mentions=allowed_mentions,
            )
        else:
            await interaction.response.send_message(content_override, embed=embed, view=view, ephemeral=is_ephemeral)
        return
    if embed is not None:
        if allowed_mentions is not None:
            await interaction.response.send_message(
                content_override,
                embed=embed,
                ephemeral=is_ephemeral,
                allowed_mentions=allowed_mentions,
            )
        else:
            await interaction.response.send_message(content_override, embed=embed, ephemeral=is_ephemeral)
        return
    if view is not None:
        if allowed_mentions is not None:
            await interaction.response.send_message(
                content,
                view=view,
                ephemeral=is_ephemeral,
                allowed_mentions=allowed_mentions,
            )
        else:
            await interaction.response.send_message(content, view=view, ephemeral=is_ephemeral)
        return
    if allowed_mentions is not None:
        await interaction.response.send_message(
            content,
            ephemeral=is_ephemeral,
            allowed_mentions=allowed_mentions,
        )
    else:
        await interaction.response.send_message(content, ephemeral=is_ephemeral)
