"""Interaction context resolution helpers for cog command handlers."""

from __future__ import annotations

import discord


def resolve_interaction_context(interaction: discord.Interaction) -> tuple[int | None, str]:
    """Return common per-interaction context used by service flows."""
    guild_id = interaction.guild.id if interaction.guild is not None else None
    display_name = getattr(interaction.user, "display_name", interaction.user.name)
    return guild_id, display_name


async def build_owner_display_name_map(
    guild: discord.Guild,
    owner_user_ids: set[int],
    interaction_user_id: int,
    interaction_display_name: str,
) -> dict[int, str]:
    """Resolve owner names with guild-display priority and API fallback."""
    resolved_names: dict[int, str] = {}
    for owner_user_id in owner_user_ids:
        if owner_user_id == interaction_user_id:
            resolved_names[owner_user_id] = interaction_display_name
            continue

        member = guild.get_member(owner_user_id)
        if member is not None:
            resolved_names[owner_user_id] = getattr(member, "display_name", member.name)
            continue

        try:
            fetched_member = await guild.fetch_member(owner_user_id)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            continue

        resolved_names[owner_user_id] = getattr(fetched_member, "display_name", fetched_member.name)

    return resolved_names
