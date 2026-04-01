"""JSON-backed player persistence for onboarding and horse adoption state."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, UTC
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2

HORSE_STATE_MIN = 0
HORSE_STATE_MAX = 100

HORSE_STATE_DEFAULTS: dict[str, int] = {
    "bond": 25,
    "energy": 70,
    "health": 75,
    "confidence": 35,
    "skill": 10,
}

HORSE_TIMESTAMP_FIELDS: tuple[str, ...] = (
    "last_fed_at",
    "last_groomed_at",
    "last_rested_at",
    "last_trained_at",
    "last_rode_at",
    "last_socialized_at",
)

HORSE_STATE_UPDATE_FIELDS: frozenset[str] = frozenset(
    {
        "bond",
        "energy",
        "health",
        "confidence",
        "skill",
        "recent_activity",
        *HORSE_TIMESTAMP_FIELDS,
    }
)

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

        horse_created_at = created_at or self._timestamp_now()
        horse_id = self._next_horse_id_for_guild(data=data, guild_id=guild_id)
        player["horse"] = self._build_new_horse_record(
            chosen_candidate=chosen_candidate,
            horse_name=name,
            created_at=horse_created_at,
            horse_id=horse_id,
        )
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

    def update_horse_state(
        self,
        user_id: int,
        guild_id: int | None,
        updates: dict[str, Any],
    ) -> PlayerRecord:
        """Persist state changes for an adopted horse using a validated update payload."""
        self._validate_supported_horse_update_fields(updates)

        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        player = data["players"].get(key)
        if player is None:
            raise RepositoryError("No player record found for horse state update.")

        horse = player.get("horse")
        if horse is None or not bool(player.get("adopted", False)):
            raise RepositoryError("Player has no adopted horse to update.")

        self._apply_horse_updates(horse=horse, updates=updates)

        player["horse"] = horse

        data["players"][key] = self._normalize_player_record(player)
        self._save_data(data)
        return deepcopy(data["players"][key])

    def update_two_horse_states(
        self,
        user_id: int,
        target_user_id: int,
        guild_id: int | None,
        updates: dict[str, Any],
        target_updates: dict[str, Any],
    ) -> tuple[PlayerRecord, PlayerRecord]:
        """Persist horse state changes for two adopted players within one save cycle."""
        self._validate_supported_horse_update_fields(updates)
        self._validate_supported_horse_update_fields(target_updates)

        data = self._load_data()
        key = self._player_key(user_id=user_id, guild_id=guild_id)
        target_key = self._player_key(user_id=target_user_id, guild_id=guild_id)
        if key == target_key:
            raise RepositoryError("Dual horse update requires two different players.")

        player = data["players"].get(key)
        target_player = data["players"].get(target_key)
        if player is None:
            raise RepositoryError("No player record found for horse state update.")
        if target_player is None:
            raise RepositoryError("No target player record found for horse state update.")

        horse = player.get("horse")
        target_horse = target_player.get("horse")
        if horse is None or not bool(player.get("adopted", False)):
            raise RepositoryError("Player has no adopted horse to update.")
        if target_horse is None or not bool(target_player.get("adopted", False)):
            raise RepositoryError("Target player has no adopted horse to update.")

        self._apply_horse_updates(horse=horse, updates=updates)
        self._apply_horse_updates(horse=target_horse, updates=target_updates)

        player["horse"] = horse
        target_player["horse"] = target_horse
        data["players"][key] = self._normalize_player_record(player)
        data["players"][target_key] = self._normalize_player_record(target_player)
        self._save_data(data)
        return deepcopy(data["players"][key]), deepcopy(data["players"][target_key])

    def list_adopted_horses_by_guild(self, guild_id: int) -> list[dict[str, Any]]:
        """Return adopted horses in a guild with stable ordering and owner linkage."""
        data = self._load_data()
        rows: list[dict[str, Any]] = []

        for player in data["players"].values():
            if int(player.get("guild_id") or 0) != guild_id:
                continue

            if not bool(player.get("adopted", False)):
                continue

            horse = player.get("horse")
            if not isinstance(horse, dict):
                continue

            horse_id = self._coerce_positive_int(horse.get("horse_id"))
            if horse_id is None:
                continue

            rows.append(
                {
                    "horse_id": horse_id,
                    "horse_name": str(horse.get("name") or "Unnamed horse"),
                    "owner_user_id": int(player["user_id"]),
                    "guild_id": guild_id,
                }
            )

        rows.sort(key=lambda row: (int(row["horse_id"]), int(row["owner_user_id"])))
        return rows

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

        schema_version = int(loaded.get("schema_version", 1))
        if schema_version > SCHEMA_VERSION:
            raise RepositoryError(
                f"Storage schema version {schema_version} is newer than supported version {SCHEMA_VERSION}."
            )

        loaded["schema_version"] = schema_version
        migrated = self._migrate_data(loaded)
        return migrated

    def _save_data(self, data: dict[str, Any]) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
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
            normalized["horse"] = self._normalize_horse_record(horse)

        return normalized

    def _normalize_horse_record(self, horse: dict[str, Any]) -> dict[str, Any]:
        return {
            "horse_id": self._coerce_positive_int(horse.get("horse_id")),
            "template_seed": horse.get("template_seed"),
            "appearance": str(horse.get("appearance", "")),
            "traits_visible": deepcopy(horse.get("traits_visible", [])),
            "hint": str(horse.get("hint", "")),
            "name": str(horse.get("name", "")),
            "created_at": self._normalize_optional_text(horse.get("created_at")),
            "first_interaction_at": self._normalize_optional_text(horse.get("first_interaction_at")),
            "last_interaction_at": self._normalize_optional_text(horse.get("last_interaction_at")),
            "bond": self._normalize_stat(horse.get("bond"), HORSE_STATE_DEFAULTS["bond"]),
            "energy": self._normalize_stat(horse.get("energy"), HORSE_STATE_DEFAULTS["energy"]),
            "health": self._normalize_stat(horse.get("health"), HORSE_STATE_DEFAULTS["health"]),
            "confidence": self._normalize_stat(horse.get("confidence"), HORSE_STATE_DEFAULTS["confidence"]),
            "skill": self._normalize_stat(horse.get("skill"), HORSE_STATE_DEFAULTS["skill"]),
            "last_fed_at": self._normalize_optional_text(horse.get("last_fed_at")),
            "last_groomed_at": self._normalize_optional_text(horse.get("last_groomed_at")),
            "last_rested_at": self._normalize_optional_text(horse.get("last_rested_at")),
            "last_trained_at": self._normalize_optional_text(horse.get("last_trained_at")),
            "last_rode_at": self._normalize_optional_text(horse.get("last_rode_at")),
            "last_socialized_at": self._normalize_optional_text(horse.get("last_socialized_at")),
            "recent_activity": self._normalize_optional_text(horse.get("recent_activity")),
        }

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

    def _build_new_horse_record(
        self,
        chosen_candidate: CandidateRecord,
        horse_name: str,
        created_at: str,
        horse_id: int,
    ) -> dict[str, Any]:
        return {
            "horse_id": horse_id,
            "template_seed": chosen_candidate.get("template_seed"),
            "appearance": chosen_candidate.get("appearance_text", ""),
            "traits_visible": deepcopy(chosen_candidate.get("traits_visible", [])),
            "hint": chosen_candidate.get("hint", ""),
            "name": horse_name,
            "created_at": created_at,
            "first_interaction_at": None,
            "last_interaction_at": None,
            "bond": HORSE_STATE_DEFAULTS["bond"],
            "energy": HORSE_STATE_DEFAULTS["energy"],
            "health": HORSE_STATE_DEFAULTS["health"],
            "confidence": HORSE_STATE_DEFAULTS["confidence"],
            "skill": HORSE_STATE_DEFAULTS["skill"],
            "last_fed_at": None,
            "last_groomed_at": None,
            "last_rested_at": None,
            "last_trained_at": None,
            "last_rode_at": None,
            "last_socialized_at": None,
            "recent_activity": None,
        }

    def _validate_supported_horse_update_fields(self, updates: dict[str, Any]) -> None:
        unknown_keys = sorted(set(updates) - HORSE_STATE_UPDATE_FIELDS)
        if unknown_keys:
            raise RepositoryError(f"Unsupported horse state fields: {', '.join(unknown_keys)}")

    def _apply_horse_updates(self, horse: dict[str, Any], updates: dict[str, Any]) -> None:
        for field, value in updates.items():
            if field in HORSE_STATE_DEFAULTS:
                current_value = self._normalize_stat(horse.get(field), HORSE_STATE_DEFAULTS[field])
                horse[field] = current_value if value is None else self._normalize_stat(value, current_value)
                continue

            if field in HORSE_TIMESTAMP_FIELDS:
                horse[field] = self._normalize_optional_text(value)
                continue

            if field == "recent_activity":
                horse[field] = self._normalize_optional_text(value)

    def _next_horse_id_for_guild(self, data: dict[str, Any], guild_id: int | None) -> int:
        used_ids: set[int] = set()
        for player in data["players"].values():
            player_guild = player.get("guild_id")
            if player_guild != guild_id:
                continue

            horse = player.get("horse")
            if not isinstance(horse, dict):
                continue

            horse_id = self._coerce_positive_int(horse.get("horse_id"))
            if horse_id is not None:
                used_ids.add(horse_id)

        next_id = 1
        while next_id in used_ids:
            next_id += 1
        return next_id

    def _migrate_data(self, data: dict[str, Any]) -> dict[str, Any]:
        migrated = deepcopy(data)
        players = migrated.get("players")
        if not isinstance(players, dict):
            raise RepositoryError("Storage payload missing players mapping.")

        if int(migrated.get("schema_version", 1)) < 2:
            self._assign_missing_horse_ids(players)

        normalized_players: dict[str, PlayerRecord] = {}
        for player_key, player_record in players.items():
            if not isinstance(player_record, dict):
                raise RepositoryError(f"Player record for key {player_key} must be an object.")
            normalized_players[player_key] = self._normalize_player_record(player_record)

        migrated["players"] = normalized_players
        migrated["schema_version"] = SCHEMA_VERSION
        return migrated

    def _assign_missing_horse_ids(self, players: dict[str, PlayerRecord]) -> None:
        scoped_players: dict[str, list[PlayerRecord]] = {}

        for player in players.values():
            if not isinstance(player, dict):
                continue

            if not bool(player.get("adopted", False)):
                continue

            horse = player.get("horse")
            if not isinstance(horse, dict):
                continue

            guild_value = player.get("guild_id")
            guild_scope = "global" if guild_value is None else str(int(guild_value))
            scoped_players.setdefault(guild_scope, []).append(player)

        for scope_players in scoped_players.values():
            used_ids: set[int] = set()
            missing: list[PlayerRecord] = []

            for player in scope_players:
                horse = player.get("horse")
                if not isinstance(horse, dict):
                    continue
                horse_id = self._coerce_positive_int(horse.get("horse_id"))
                if horse_id is None or horse_id in used_ids:
                    horse["horse_id"] = None
                    missing.append(player)
                    continue
                horse["horse_id"] = horse_id
                used_ids.add(horse_id)

            # Stable id migration must be deterministic to keep roster ordering consistent.
            missing.sort(key=self._migration_horse_sort_key)
            next_id = 1
            for player in missing:
                while next_id in used_ids:
                    next_id += 1
                horse = player.get("horse")
                if isinstance(horse, dict):
                    horse["horse_id"] = next_id
                used_ids.add(next_id)
                next_id += 1

    def _migration_horse_sort_key(self, player: PlayerRecord) -> tuple[str, int, str]:
        horse = player.get("horse")
        if not isinstance(horse, dict):
            return ("", 0, "")
        return (
            str(horse.get("created_at") or ""),
            int(player.get("user_id") or 0),
            str(horse.get("name") or ""),
        )

    def _coerce_positive_int(self, value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        if parsed < 1:
            return None
        return parsed

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _normalize_stat(self, value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(HORSE_STATE_MIN, min(HORSE_STATE_MAX, parsed))
