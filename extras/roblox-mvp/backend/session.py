from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

APP_NAME = "roblox-mvp"
PLANNER_AGENT = "roblox-mvp-spec"
DOC_FILES = ("gameplay.md", "levels.md", "acceptance.md")


def seed_prompt(project_dir: Path) -> str:
    files = ", ".join(DOC_FILES)
    return (
        f"PROJECT_DIR={project_dir}\n\n"
        f"Write {files} in that folder root. Do not write anywhere else. "
        f"Do not ask for a folder. Ignore any later path the user types.\n"
        f"Interview for one mechanic and one scene, then write the three files "
        f"and stop. Do not spawn roblox-mvp-builder until the user explicitly "
        f"confirms the files (e.g. 确认，开始搭).\n"
        f"You have no Studio tools."
    )


def dispatch_seed_turn(state: Any, slot: Any, message: str) -> None:
    from kiro_crew.dashboard.chat_runner import _run_chat
    from kiro_crew.dashboard.turn_dispatch import bounded_chat_turn

    slot.append("user", message)
    task = asyncio.create_task(bounded_chat_turn(_run_chat(state, slot, message)))
    slot.task = task
    state._background_tasks.add(task)
    task.add_done_callback(state._background_tasks.discard)
    state.push_slots_update()


def start_planner_session(state: Any, project_dir: Path) -> dict[str, str]:
    slot = state.get_or_create_slot(agent=PLANNER_AGENT, app=APP_NAME)
    try:
        slot.title = f"Roblox MVP: {project_dir.name}"
        slot._titled = True
        if hasattr(state, "push_slot_title"):
            state.push_slot_title(slot.key, slot.title)
    except Exception:
        logger.debug("title set failed", exc_info=True)
    dispatch_seed_turn(state, slot, seed_prompt(project_dir))
    return {"slot": slot.key, "project_dir": str(project_dir)}
