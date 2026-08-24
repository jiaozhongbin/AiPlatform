from __future__ import annotations

import asyncio
import threading
from typing import Any

from aiohttp import web

from kiro_crew.apps.context import AppContext
from kiro_crew.apps.route_registry import AppRoute

from backend.paths import safe_project_dir
from backend.picker import PickerError, pick_folder_sync
from backend.session import start_planner_session

_PICK_LOCK = threading.Lock()


async def handle_pick_folder(request: web.Request, ctx: AppContext) -> web.Response:
    if not _PICK_LOCK.acquire(blocking=False):
        return web.json_response(
            {"code": "picker_busy", "error": "a folder picker is already open"},
            status=409,
        )
    try:
        path = await asyncio.to_thread(pick_folder_sync)
    except PickerError as exc:
        status = 501 if exc.code in {"folder_chooser_unsupported", "picker_unavailable"} else 500
        if exc.code == "picker_timeout":
            status = 408
        return web.json_response({"code": exc.code, "error": str(exc)}, status=status)
    finally:
        _PICK_LOCK.release()
    return web.json_response({"path": path, "cancelled": path is None})


async def handle_start(request: web.Request, ctx: AppContext) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"code": "invalid_json", "error": "JSON body required"}, status=400)
    raw = ""
    if isinstance(body, dict):
        raw = str(body.get("project_dir") or "")
    project_dir = await asyncio.to_thread(safe_project_dir, raw)
    if project_dir is None:
        return web.json_response(
            {"code": "invalid_project_dir", "error": "absolute existing directory required"},
            status=400,
        )
    state = request.app.get("state")
    if state is None:
        return web.json_response({"code": "no_gateway_state", "error": "gateway state missing"}, status=500)
    result = start_planner_session(state, project_dir)
    return web.json_response(result, status=201)


def register_routes(ctx: AppContext) -> list[AppRoute]:
    return [
        AppRoute(method="POST", path="/pick-folder", handler=handle_pick_folder),
        AppRoute(method="POST", path="/start", handler=handle_start),
    ]
