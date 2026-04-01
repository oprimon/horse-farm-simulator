"""Interaction context resolution helpers for cog command handlers."""

from __future__ import annotations

import asyncio

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
    allow_fetch: bool = True,
) -> dict[int, str]:
    """Resolve owner names with guild-display priority and concurrent API fallback."""
    resolved_names: dict[int, str] = {}
    ids_to_fetch: list[int] = []

    for owner_user_id in owner_user_ids:
        if owner_user_id == interaction_user_id:
            resolved_names[owner_user_id] = interaction_display_name
            continue

        member = guild.get_member(owner_user_id)
        if member is not None:
            resolved_names[owner_user_id] = getattr(member, "display_name", member.name)
            continue

        if allow_fetch:
            ids_to_fetch.append(owner_user_id)

    if ids_to_fetch:
        fetch_results = await asyncio.gather(
            *(guild.fetch_member(uid) for uid in ids_to_fetch),
            return_exceptions=True,
        )
        for uid, result in zip(ids_to_fetch, fetch_results):
            if isinstance(result, BaseException):
                continue
            resolved_names[uid] = getattr(result, "display_name", result.name)

    return resolved_names
