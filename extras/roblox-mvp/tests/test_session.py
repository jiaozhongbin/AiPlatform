from __future__ import annotations

from collections.abc import Awaitable
from pathlib import Path

import pytest

from backend.session import (
    APP_NAME,
    DOC_FILES,
    PLANNER_AGENT,
    dispatch_seed_turn,
    seed_prompt,
    start_planner_session,
)


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


@pytest.mark.asyncio
async def test_dispatch_seed_registers_stoppable_task(monkeypatch: pytest.MonkeyPatch) -> None:
    class Slot:
        def __init__(self) -> None:
            self.task = None
            self.appended: list[tuple[str, str]] = []

        def append(self, role: str, message: str) -> None:
            self.appended.append((role, message))

    class State:
        def __init__(self) -> None:
            self._background_tasks: set[object] = set()
            self.pushed = 0

        def push_slots_update(self) -> None:
            self.pushed += 1

    async def _fake_run(state: object, slot: object, message: str) -> None:
        return None

    async def _fake_bounded(coro: Awaitable[None]) -> None:
        await coro

    monkeypatch.setattr("kiro_crew.dashboard.chat_runner._run_chat", _fake_run)
    monkeypatch.setattr("kiro_crew.dashboard.turn_dispatch.bounded_chat_turn", _fake_bounded)

    slot = Slot()
    state = State()
    dispatch_seed_turn(state, slot, "seed")
    assert slot.appended == [("user", "seed")]
    assert slot.task is not None
    assert slot.task in state._background_tasks
    assert state.pushed == 1
    await slot.task
    assert slot.task not in state._background_tasks
