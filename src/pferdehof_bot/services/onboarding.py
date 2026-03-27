"""Shared onboarding presentation models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PresentationField:
    """Single field entry for structured Discord response rendering."""

    name: str
    value: str
    inline: bool = False


@dataclass(frozen=True)
class ResponsePresentation:
    """Structured presentation payload used by Discord transport renderers."""

    title: str
    description: str
    fields: tuple[PresentationField, ...] = ()
    accent: str | None = None
    footer: str | None = None
