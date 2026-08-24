from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from kiro_crew.apps.context import AppContext
from kiro_crew.apps.route_registry import AppRoute
from backend.picker import PickerError
from backend.routes import register_routes


def _ctx(tmp_path: Path) -> AppContext:
    return AppContext(name="roblox-mvp", data_dir=tmp_path)


class _StubRequest:
    def __init__(self, body: dict[str, Any] | None = None, state: Any = None) -> None:
        self._body = body if body is not None else {}
        self.app = {"state": state}

    async def json(self) -> dict[str, Any]:
        return self._body


def test_register_routes_lists_pick_and_start(tmp_path: Path) -> None:
    routes = register_routes(_ctx(tmp_path))
    pairs = {(r.method, r.path) for r in routes}
    assert ("POST", "/pick-folder") in pairs
    assert ("POST", "/start") in pairs
    assert all(isinstance(r, AppRoute) for r in routes)


@pytest.mark.asyncio
async def test_start_rejects_relative_path(tmp_path: Path) -> None:
    routes = {r.path: r for r in register_routes(_ctx(tmp_path))}
    req = _StubRequest({"project_dir": "relative"})
    resp = await routes["/start"].handler(req, _ctx(tmp_path))
    assert resp.status == 400
    body = json.loads(resp.text)
    assert body["code"] == "invalid_project_dir"


@pytest.mark.asyncio
async def test_start_returns_slot_and_project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _stub_start(state: Any, project_dir: Path) -> dict[str, str]:
        return {"slot": "roblox-mvp-1", "project_dir": str(project_dir)}

    monkeypatch.setattr("backend.routes.start_planner_session", _stub_start)
    routes = {r.path: r for r in register_routes(_ctx(tmp_path))}
    req = _StubRequest({"project_dir": str(tmp_path)}, state=object())
    resp = await routes["/start"].handler(req, _ctx(tmp_path))
    assert resp.status == 201
    body = json.loads(resp.text)
    assert body["slot"] == "roblox-mvp-1"
    assert Path(body["project_dir"]) == tmp_path.resolve()


@pytest.mark.asyncio
async def test_pick_folder_unsupported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> str | None:
        raise PickerError("folder chooser is not available on this host", "folder_chooser_unsupported")

    monkeypatch.setattr("backend.routes.pick_folder_sync", _raise)
    routes = {r.path: r for r in register_routes(_ctx(tmp_path))}
    resp = await routes["/pick-folder"].handler(_StubRequest(), _ctx(tmp_path))
    assert resp.status == 501
    body = json.loads(resp.text)
    assert body["code"] == "folder_chooser_unsupported"


@pytest.mark.asyncio
async def test_pick_folder_cancelled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.routes.pick_folder_sync", lambda: None)
    routes = {r.path: r for r in register_routes(_ctx(tmp_path))}
    resp = await routes["/pick-folder"].handler(_StubRequest(), _ctx(tmp_path))
    assert resp.status == 200
    body = json.loads(resp.text)
    assert body["cancelled"] is True
    assert body["path"] is None


@pytest.mark.asyncio
async def test_pick_folder_busy(tmp_path: Path) -> None:
    from backend import routes as routes_mod

    assert routes_mod._PICK_LOCK.acquire(blocking=False)
    try:
        routes = {r.path: r for r in register_routes(_ctx(tmp_path))}
        resp = await routes["/pick-folder"].handler(_StubRequest(), _ctx(tmp_path))
        assert resp.status == 409
        body = json.loads(resp.text)
        assert body["code"] == "picker_busy"
    finally:
        routes_mod._PICK_LOCK.release()
