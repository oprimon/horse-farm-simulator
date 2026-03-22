"""JSON-backed player persistence for onboarding and horse adoption state."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, UTC
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1

CandidateRecord = dict[str, Any]
PlayerRecord = dict[str, Any]


class RepositoryError(Exception):
    """Raised when repository operations fail validation or state checks."""


class AdoptionConflictError(RepositoryError):
    """Raised when an operation would create conflicting horse adoption state."""


class JsonPlayerRepository:
    """Repository that persists player records to a local JSON file."""

    def __init__(self, storage_path: str | Path) -> None:
        self._storage_path = Path(storage_path)

    def get_player(self, user_id: int, guild_id: int | None) -> PlayerRecord | None:
        """Return a deep copy of a player's record when it exists."""
        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        player = data["players"].get(key)
        if player is None:
            return None
        return deepcopy(player)

    def upsert_player(self, record: PlayerRecord) -> PlayerRecord:
        """Insert or replace a player record while protecting adoption invariants."""
        user_id = int(record["user_id"])
        guild_id_raw = record.get("guild_id")
        guild_id = int(guild_id_raw) if guild_id_raw is not None else None

        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        existing = data["players"].get(key)
        normalized_record = self._normalize_player_record(record)

        if existing is not None:
            self._ensure_no_adoption_conflict(existing=existing, incoming=normalized_record)

        data["players"][key] = normalized_record
        self._save_data(data)
        return deepcopy(normalized_record)

    def start_onboarding(
        self,
        user_id: int,
        guild_id: int | None,
        candidates: list[CandidateRecord],
        created_at: str | None = None,
    ) -> PlayerRecord:
        """Start or replace onboarding data for a non-adopted player."""
        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        player = data["players"].get(key) or self._new_player_record(user_id=user_id, guild_id=guild_id)

        if bool(player.get("adopted", False)):
            raise AdoptionConflictError("Player already adopted a horse.")

        player["onboarding_session"] = {
            "active": True,
            "candidates": deepcopy(candidates),
            "chosen_candidate_id": None,
            "created_at": created_at or self._timestamp_now(),
        }

        data["players"][key] = self._normalize_player_record(player)
        self._save_data(data)
        return deepcopy(data["players"][key])

    def set_chosen_candidate(self, user_id: int, guild_id: int | None, candidate_id: str) -> PlayerRecord:
        """Persist the selected candidate id for an active onboarding session."""
        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        player = data["players"].get(key)
        if player is None:
            raise RepositoryError("No player record found for candidate selection.")

        session = player.get("onboarding_session") or {}
        if not bool(session.get("active", False)):
            raise RepositoryError("No active onboarding session.")

        session["chosen_candidate_id"] = candidate_id
        player["onboarding_session"] = session

        data["players"][key] = self._normalize_player_record(player)
        self._save_data(data)
        return deepcopy(data["players"][key])

    def finalize_horse_name(
        self,
        user_id: int,
        guild_id: int | None,
        name: str,
        created_at: str | None = None,
    ) -> PlayerRecord:
        """Finalize adoption by creating the player's horse from the chosen candidate."""
        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        player = data["players"].get(key)
        if player is None:
            raise RepositoryError("No player record found for naming.")

        if bool(player.get("adopted", False)):
            raise AdoptionConflictError("Player already adopted a horse.")

        session = player.get("onboarding_session") or {}
        if not bool(session.get("active", False)):
            raise RepositoryError("No active onboarding session.")

        chosen_id = session.get("chosen_candidate_id")
        if not chosen_id:
            raise RepositoryError("No chosen candidate to finalize.")

        chosen_candidate = self._find_candidate(
            candidates=session.get("candidates", []),
            candidate_id=str(chosen_id),
        )
        if chosen_candidate is None:
            raise RepositoryError("Chosen candidate does not exist in onboarding session.")

        player["horse"] = {
            "template_seed": chosen_candidate.get("template_seed"),
            "appearance": chosen_candidate.get("appearance_text", ""),
            "traits_visible": deepcopy(chosen_candidate.get("traits_visible", [])),
            "hint": chosen_candidate.get("hint", ""),
            "name": name,
            "created_at": created_at or self._timestamp_now(),
            "first_interaction_at": None,
            "last_interaction_at": None,
        }
        player["adopted"] = True
        player["onboarding_session"] = {
            "active": False,
            "candidates": [],
            "chosen_candidate_id": None,
            "created_at": session.get("created_at"),
        }

        data["players"][key] = self._normalize_player_record(player)
        self._save_data(data)
        return deepcopy(data["players"][key])

    def record_horse_interaction(
        self,
        user_id: int,
        guild_id: int | None,
        interacted_at: str | None = None,
    ) -> tuple[PlayerRecord, bool]:
        """Persist horse interaction timestamps and report whether it was the first one."""
        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        player = data["players"].get(key)
        if player is None:
            raise RepositoryError("No player record found for horse interaction.")

        horse = player.get("horse")
        if horse is None or not bool(player.get("adopted", False)):
            raise RepositoryError("No adopted horse found for interaction.")

        interaction_timestamp = interacted_at or self._timestamp_now()
        first_interaction = not bool(horse.get("first_interaction_at"))
        if first_interaction:
            horse["first_interaction_at"] = interaction_timestamp
        horse["last_interaction_at"] = interaction_timestamp
        player["horse"] = horse

        data["players"][key] = self._normalize_player_record(player)
        self._save_data(data)
        return deepcopy(data["players"][key]), first_interaction

    def admin_rename_horse(self, user_id: int, guild_id: int | None, new_name: str) -> PlayerRecord:
        """Override an adopted player's horse name as an admin moderation action."""
        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        player = data["players"].get(key)
        if player is None:
            raise RepositoryError("No player record found for admin rename.")

        horse = player.get("horse")
        if horse is None or not bool(player.get("adopted", False)):
            raise RepositoryError("Player has no adopted horse to rename.")

        horse["name"] = new_name
        player["horse"] = horse

        data["players"][key] = self._normalize_player_record(player)
        self._save_data(data)
        return deepcopy(data["players"][key])

    def _load_data(self) -> dict[str, Any]:
        if not self._storage_path.exists():
            return {"schema_version": SCHEMA_VERSION, "players": {}}

        with self._storage_path.open("r", encoding="utf-8") as storage_file:
            loaded = json.load(storage_file)

        if not isinstance(loaded, dict):
            raise RepositoryError("Storage payload must be an object.")

        players = loaded.get("players")
        if not isinstance(players, dict):
            raise RepositoryError("Storage payload missing players mapping.")

        loaded.setdefault("schema_version", SCHEMA_VERSION)
        return loaded

    def _save_data(self, data: dict[str, Any]) -> None:
        payload = {
            "schema_version": data.get("schema_version", SCHEMA_VERSION),
            "players": data["players"],
        }
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as storage_file:
            json.dump(payload, storage_file, indent=2)

    def _player_key(self, user_id: int, guild_id: int | None) -> str:
        guild_scope = "global" if guild_id is None else str(guild_id)
        return f"{user_id}:{guild_scope}"

    def _new_player_record(self, user_id: int, guild_id: int | None) -> PlayerRecord:
        return {
            "user_id": user_id,
            "guild_id": guild_id,
            "adopted": False,
            "onboarding_session": {
                "active": False,
                "candidates": [],
                "chosen_candidate_id": None,
                "created_at": None,
            },
            "horse": None,
        }

    def _normalize_player_record(self, record: PlayerRecord) -> PlayerRecord:
        normalized = self._new_player_record(
            user_id=int(record["user_id"]),
            guild_id=int(record["guild_id"]) if record.get("guild_id") is not None else None,
        )

        normalized["adopted"] = bool(record.get("adopted", False))

        onboarding = record.get("onboarding_session") or {}
        normalized["onboarding_session"] = {
            "active": bool(onboarding.get("active", False)),
            "candidates": deepcopy(onboarding.get("candidates", [])),
            "chosen_candidate_id": onboarding.get("chosen_candidate_id"),
            "created_at": onboarding.get("created_at"),
        }

        horse = record.get("horse")
        if horse is None:
            normalized["horse"] = None
        else:
            normalized["horse"] = {
                "template_seed": horse.get("template_seed"),
                "appearance": horse.get("appearance", ""),
                "traits_visible": deepcopy(horse.get("traits_visible", [])),
                "hint": horse.get("hint", ""),
                "name": horse.get("name", ""),
                "created_at": horse.get("created_at"),
                "first_interaction_at": horse.get("first_interaction_at"),
                "last_interaction_at": horse.get("last_interaction_at"),
            }

        return normalized

    def _ensure_no_adoption_conflict(self, existing: PlayerRecord, incoming: PlayerRecord) -> None:
        existing_adopted = bool(existing.get("adopted", False))
        incoming_adopted = bool(incoming.get("adopted", False))

        if existing_adopted and not incoming_adopted:
            raise AdoptionConflictError("Cannot unset adoption state once a horse is adopted.")

        if existing_adopted and incoming_adopted:
            existing_name = (existing.get("horse") or {}).get("name")
            incoming_name = (incoming.get("horse") or {}).get("name")
            if existing_name != incoming_name:
                raise AdoptionConflictError("Player cannot hold multiple adopted horses.")

    def _find_candidate(
        self,
        candidates: list[CandidateRecord],
        candidate_id: str,
    ) -> CandidateRecord | None:
        for candidate in candidates:
            if str(candidate.get("id", "")).upper() == candidate_id.upper():
                return candidate
        return None

    def _timestamp_now(self) -> str:
        return datetime.now(UTC).isoformat()
