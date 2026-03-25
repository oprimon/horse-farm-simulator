"""Documentation guardrails for MVP-002 exit validation and MVP-003 handoff."""

from __future__ import annotations

from pathlib import Path


def _read_readme() -> str:
    return Path("README.md").read_text(encoding="utf-8")


def test_readme_contains_mvp002_exit_checklist_section() -> None:
    readme = _read_readme()

    assert "## MVP-002 Exit Checklist" in readme
    assert "PASS: Adopted players can use care commands, train, and ride reliably." in readme
    assert "PASS: Horse state changes persist across restarts." in readme
    assert "PASS: Ride outcomes visibly reflect horse state." in readme
    assert "PASS: Telemetry captures enough data to measure loop completion and repeat usage." in readme


def test_readme_contains_mvp003_handoff_and_start_command() -> None:
    readme = _read_readme()

    assert "## MVP-003 Handoff Recommendation" in readme
    assert "Next session start command (MVP-003 planning):" in readme
    assert "d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q" in readme
