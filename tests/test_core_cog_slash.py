"""Tests for core slash command registration and transport migration."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import discord

from pferdehof_bot.bot import create_bot, load_extensions
from pferdehof_bot.cogs.core import CoreCog
from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services.onboarding import PresentationField, ResponsePresentation


def test_core_cog_registers_slash_commands() -> None:
    bot = create_bot()
    asyncio.run(load_extensions(bot))

    commands_by_name = {command.name: command for command in bot.tree.get_commands()}
    assert "start" in commands_by_name
    assert "greet" in commands_by_name
    assert "feed" in commands_by_name
    assert "groom" in commands_by_name
    assert "rest" in commands_by_name
    assert "train" in commands_by_name
    assert "ride" in commands_by_name
    assert "stable" in commands_by_name
    assert "horse" in commands_by_name

    horse_group = commands_by_name["horse"]
    assert isinstance(horse_group, discord.app_commands.Group)

    subcommands_by_name = {command.name: command for command in horse_group.commands}
    assert "profile" in subcommands_by_name
    assert "view" in subcommands_by_name
    assert "choose" in subcommands_by_name
    assert "name" in subcommands_by_name
    assert "rename" in subcommands_by_name

    rename_command = subcommands_by_name["rename"]
    assert rename_command.default_permissions is not None
    assert rename_command.default_permissions.administrator is True


def test_prefix_command_handlers_are_not_registered_after_migration() -> None:
    bot = create_bot()
    asyncio.run(load_extensions(bot))

    assert bot.get_command("start") is None
    assert bot.get_command("greet") is None
    assert bot.get_command("feed") is None
    assert bot.get_command("groom") is None
    assert bot.get_command("rest") is None
    assert bot.get_command("train") is None
    assert bot.get_command("ride") is None
    assert bot.get_command("stable") is None
    assert bot.get_command("horse") is None


class _FakeGuild:
    def __init__(self, members: dict[int, object], fetch_results: dict[int, object], fetch_errors: dict[int, Exception]) -> None:
        self._members = members
        self._fetch_results = fetch_results
        self._fetch_errors = fetch_errors
        self.fetch_calls: list[int] = []

    def get_member(self, user_id: int) -> object | None:
        return self._members.get(user_id)

    async def fetch_member(self, user_id: int) -> object:
        self.fetch_calls.append(user_id)
        if user_id in self._fetch_errors:
            raise self._fetch_errors[user_id]
        return self._fetch_results[user_id]


class _FakeInteractionResponse:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def send_message(
        self,
        content: str,
        *,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        ephemeral: bool = False,
    ) -> None:
        self.calls.append(
            {
                "content": content,
                "embed": embed,
                "view": view,
                "ephemeral": ephemeral,
            }
        )


class _FakeInteraction:
    def __init__(self) -> None:
        self.response = _FakeInteractionResponse()


def _build_core_cog(tmp_path: Path) -> CoreCog:
    bot = create_bot()
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    return CoreCog(bot=bot, repository=repository)


def test_build_owner_display_name_map_prefers_interaction_name_and_cache_then_fetch(tmp_path) -> None:
    core_cog = _build_core_cog(tmp_path)
    cached_member = SimpleNamespace(name="OldName", display_name="Cached Rider")
    fetched_member = SimpleNamespace(name="FetchedName", display_name="Fetched Rider")
    guild = _FakeGuild(
        members={102: cached_member},
        fetch_results={103: fetched_member},
        fetch_errors={},
    )

    resolved = asyncio.run(
        core_cog._build_owner_display_name_map(
            guild=guild,  # type: ignore[arg-type]
            owner_user_ids={101, 102, 103},
            interaction_user_id=101,
            interaction_display_name="Current Rider",
        )
    )

    assert resolved == {
        101: "Current Rider",
        102: "Cached Rider",
        103: "Fetched Rider",
    }
    assert guild.fetch_calls == [103]


def test_build_owner_display_name_map_skips_unresolvable_users(tmp_path) -> None:
    core_cog = _build_core_cog(tmp_path)
    guild = _FakeGuild(
        members={},
        fetch_results={},
        fetch_errors={
            200: discord.NotFound(response=SimpleNamespace(status=404, reason="missing"), message="missing"),
            201: discord.Forbidden(response=SimpleNamespace(status=403, reason="forbidden"), message="forbidden"),
        },
    )

    resolved = asyncio.run(
        core_cog._build_owner_display_name_map(
            guild=guild,  # type: ignore[arg-type]
            owner_user_ids={200, 201},
            interaction_user_id=999,
            interaction_display_name="Current Rider",
        )
    )

    assert resolved == {}
    assert guild.fetch_calls == [200, 201]


def test_send_response_uses_embed_when_presentation_is_provided(tmp_path) -> None:
    core_cog = _build_core_cog(tmp_path)
    interaction = _FakeInteraction()
    presentation = ResponsePresentation(
        title="Welcome To Pferdehof",
        description="Three horses are waiting to meet you.",
        fields=(
            PresentationField(name="Next Step", value="Run `/horse view` to meet your candidates."),
        ),
        accent="success",
        footer="Adoption journey started",
    )

    asyncio.run(
        core_cog._send_response(
            interaction=interaction,  # type: ignore[arg-type]
            command_id="start",
            message="fallback text",
            presentation=presentation,
        )
    )

    assert len(interaction.response.calls) == 1
    sent = interaction.response.calls[0]
    assert sent["content"] == "fallback text"
    assert sent["ephemeral"] is False
    embed = sent["embed"]
    assert isinstance(embed, discord.Embed)
    assert embed.title == "Welcome To Pferdehof"
    assert embed.description == "Three horses are waiting to meet you."
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Next Step"
    assert embed.fields[0].value == "Run `/horse view` to meet your candidates."


def test_send_response_without_presentation_sends_text_only(tmp_path) -> None:
    core_cog = _build_core_cog(tmp_path)
    interaction = _FakeInteraction()

    asyncio.run(
        core_cog._send_response(
            interaction=interaction,  # type: ignore[arg-type]
            command_id="start",
            message="text only",
        )
    )

    assert len(interaction.response.calls) == 1
    sent = interaction.response.calls[0]
    assert sent["content"] == "text only"
    assert sent["embed"] is None
    assert sent["view"] is None
    assert sent["ephemeral"] is False


def test_build_candidate_view_builds_buttons_for_known_candidate_ids(tmp_path) -> None:
    core_cog = _build_core_cog(tmp_path)
    candidates = [
        {"id": "A", "appearance_text": "Chestnut"},
        {"id": "B", "appearance_text": "Bay"},
        {"id": "C", "appearance_text": "Grey"},
    ]

    view = core_cog._build_candidate_view(candidates=candidates, owner_user_id=101)

    assert view is not None
    assert len(view.children) == 3
    labels = [item.label for item in view.children if isinstance(item, discord.ui.Button)]
    assert labels == ["Adopt A", "Adopt B", "Adopt C"]


def test_build_candidate_view_returns_none_without_valid_candidates(tmp_path) -> None:
    core_cog = _build_core_cog(tmp_path)
    candidates = [{"id": "Z"}]

    view = core_cog._build_candidate_view(candidates=candidates, owner_user_id=101)

    assert view is None


def test_candidate_view_rejects_interaction_from_wrong_user(tmp_path) -> None:
    """A user who did not open /horse view cannot choose via the button panel."""
    core_cog = _build_core_cog(tmp_path)
    candidates = [
        {"id": "A", "appearance_text": "Chestnut"},
        {"id": "B", "appearance_text": "Bay"},
        {"id": "C", "appearance_text": "Grey"},
    ]
    view = core_cog._build_candidate_view(candidates=candidates, owner_user_id=101)
    assert view is not None

    intruder_response = _FakeInteractionResponse()
    intruder_interaction = _FakeInteraction()
    intruder_interaction.response = intruder_response
    intruder_interaction.user = SimpleNamespace(id=999, name="Intruder", display_name="Intruder")
    intruder_interaction.guild = None

    asyncio.run(view._handle_choice(interaction=intruder_interaction, candidate_id="A"))  # type: ignore[arg-type]

    assert len(intruder_response.calls) == 1
    call = intruder_response.calls[0]
    assert call["ephemeral"] is True
    assert "Only the player" in call["content"]
    # Buttons must still be enabled after an unauthorized attempt.
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert all(not btn.disabled for btn in buttons)


def test_candidate_view_disables_buttons_after_successful_choice(tmp_path) -> None:
    """Buttons become disabled and the view stops after a valid selection."""
    from pferdehof_bot.repositories import JsonPlayerRepository

    storage_path = tmp_path / "players.json"
    repository = JsonPlayerRepository(storage_path=storage_path)
    repository.start_onboarding(
        user_id=200,
        guild_id=300,
        candidates=[
            {"id": "A", "appearance_text": "Chestnut", "hint": "Brave", "template_seed": 1},
            {"id": "B", "appearance_text": "Bay", "hint": "Calm", "template_seed": 2},
            {"id": "C", "appearance_text": "Grey", "hint": "Curious", "template_seed": 3},
        ],
    )
    bot = create_bot()
    cog = CoreCog(bot=bot, repository=repository)
    candidates = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    view = cog._build_candidate_view(candidates=candidates, owner_user_id=200)
    assert view is not None

    owner_response = _FakeInteractionResponse()
    owner_interaction = _FakeInteraction()
    owner_interaction.response = owner_response
    owner_interaction.user = SimpleNamespace(id=200, name="Rider", display_name="Rider")
    owner_interaction.guild = SimpleNamespace(id=300)

    asyncio.run(view._handle_choice(interaction=owner_interaction, candidate_id="B"))  # type: ignore[arg-type]

    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert all(btn.disabled for btn in buttons)
    assert len(owner_response.calls) == 1
    assert "B" in owner_response.calls[0]["content"]


def test_candidate_view_on_timeout_disables_all_buttons(tmp_path) -> None:
    """on_timeout disables every button so an expired panel is visually clear."""
    core_cog = _build_core_cog(tmp_path)
    candidates = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    view = core_cog._build_candidate_view(candidates=candidates, owner_user_id=101)
    assert view is not None

    asyncio.run(view.on_timeout())

    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert all(btn.disabled for btn in buttons)
