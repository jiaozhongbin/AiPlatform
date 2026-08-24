from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.session import DOC_FILES, PLANNER_AGENT, APP_NAME, seed_prompt, start_planner_session


def test_seed_names_project_dir_and_files(tmp_path: Path) -> None:
    text = seed_prompt(tmp_path)
    assert f"PROJECT_DIR={tmp_path}" in text.replace("\\", "/") or str(tmp_path) in text
    for name in DOC_FILES:
        assert name in text
    assert "roblox-mvp-builder" in text


class _Slot:
    def __init__(self) -> None:
        self.key = "roblox-mvp-1"
        self.appended: list[tuple[str, str]] = []

    def append(self, role: str, message: str) -> None:
        self.appended.append((role, message))


def test_start_creates_planner_slot_and_dispatches(tmp_path: Path, monkeypatch) -> None:
    slot = _Slot()
    created: dict = {}

    class State:
        def get_or_create_slot(self, **kwargs):
            created.update(kwargs)
            return slot

    dispatched: list = []
    monkeypatch.setattr(
        "backend.session.dispatch_seed_turn",
        lambda state, s, msg: dispatched.append((s.key, msg)),
    )
    out = start_planner_session(State(), tmp_path)
    assert created["agent"] == PLANNER_AGENT
    assert created["app"] == APP_NAME
    assert out["slot"] == "roblox-mvp-1"
    assert Path(out["project_dir"]) == tmp_path
    assert dispatched and DOC_FILES[0] in dispatched[0][1]
