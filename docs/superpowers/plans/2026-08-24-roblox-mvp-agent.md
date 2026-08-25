# Roblox MVP Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a local (non-builtin) Kiro Crew app at `extras/roblox-mvp/` with
a start-page folder pick, a planner agent that writes three markdown files,
and a builder agent that drafts in Roblox Studio after explicit confirmation.

**Architecture:** In-gateway `backend.hooks.routes` handlers validate
`PROJECT_DIR`, open a planner slot, and seed it. The planner template has no
Studio MCP; it may spawn only `roblox-mvp-builder`. The builder template owns
the Studio server and an explicit draft-only tool allowlist. The start page
is the app's own `ui/` bundle, not `website/src/apps/`.

**Tech Stack:** Python 3.10+, aiohttp, `kiro_crew.security.is_sensitive_path`,
`kiro_crew.platform_compat.trusted_system_bin`, App Kit hooks/routes, React +
Vite for the start page, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-roblox-mvp-agent-design.md`

## Global Constraints

- Do not add anything under `src/kiro_crew/apps/builtins/`.
- Do not add this app to the default pytest `testpaths` (keep public CI unchanged).
- `agent.model` is `"auto"` on both templates. No hardcoded model id.
- User-facing start-page copy is Chinese. No emoji icons; `lucide-react` with
  `className="lucide-inline"` if an icon is used.
- Non-2xx JSON bodies include a machine-readable `code` field.
- Filesystem and subprocess work run in `asyncio.to_thread`, never on the loop.
- Process launches go through `platform_compat.trusted_system_bin`. Never a
  bare `powershell` / `osascript` PATH lookup.
- `PROJECT_DIR` must be absolute, an existing directory, and not
  `is_sensitive_path`. v1 does not create missing parents.
- Planner `tools` must not contain `@roblox-studio` or a Studio `mcpServers` key.
- Builder `tools` must not contain `use_subagent`, `publish`, `commit`, or
  `delete`.
- Do not touch `CHANGELOG.md`. Do not push.

---

## File map

| Path | Responsibility |
|---|---|
| `extras/roblox-mvp/backend/paths.py` | `safe_project_dir(raw) -> Path \| None` |
| `extras/roblox-mvp/backend/picker.py` | `pick_folder_supported()`, `pick_folder_sync()` |
| `extras/roblox-mvp/backend/session.py` | `seed_prompt(project_dir)`, `start_planner_session(state, project_dir)` |
| `extras/roblox-mvp/backend/routes.py` | `register_routes(ctx) -> list[AppRoute]` |
| `extras/roblox-mvp/agents/roblox-mvp-spec.json` | Planner template |
| `extras/roblox-mvp/agents/roblox-mvp-builder.json` | Builder template |
| `extras/roblox-mvp/prompts/spec.md` | Planner system prompt |
| `extras/roblox-mvp/prompts/builder.md` | Builder system prompt |
| `extras/roblox-mvp/skills/roblox-mvp-docs/SKILL.md` | Planner skill |
| `extras/roblox-mvp/skills/roblox-studio-draft/SKILL.md` | Builder draft rules |
| `extras/roblox-mvp/skills/roblox-mvp-build/SKILL.md` | Builder mapping rules |
| `extras/roblox-mvp/app.json` | Manifest |
| `extras/roblox-mvp/ui/` | Start page |
| `extras/roblox-mvp/tests/` | Pytest (run explicitly) |
| `extras/roblox-mvp/README.md` | Install + MCP command to fill in |

---

### Task 1: Project-dir validation

**Files:**
- Create: `extras/roblox-mvp/backend/__init__.py` (empty)
- Create: `extras/roblox-mvp/backend/paths.py`
- Create: `extras/roblox-mvp/tests/conftest.py`
- Test: `extras/roblox-mvp/tests/test_paths.py`

**Interfaces:**
- Consumes: `kiro_crew.security.is_sensitive_path(path_str: str, base_dir: str | None = None) -> bool`
- Produces: `safe_project_dir(raw: str) -> Path | None`

- [ ] **Step 1: Write the failing tests**

```python
# extras/roblox-mvp/tests/conftest.py
from __future__ import annotations

import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[1]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))
```

```python
# extras/roblox-mvp/tests/test_paths.py
from __future__ import annotations

import os
from pathlib import Path

from backend.paths import safe_project_dir


def test_rejects_empty_and_relative(tmp_path: Path) -> None:
    assert safe_project_dir("") is None
    assert safe_project_dir("   ") is None
    assert safe_project_dir("relative/folder") is None
    assert safe_project_dir(str(tmp_path / "missing")) is None


def test_accepts_existing_absolute_dir(tmp_path: Path) -> None:
    got = safe_project_dir(str(tmp_path))
    assert got == tmp_path.resolve()


def test_rejects_file_not_dir(tmp_path: Path) -> None:
    f = tmp_path / "not-a-dir"
    f.write_text("x", encoding="utf-8")
    assert safe_project_dir(str(f)) is None


def test_rejects_sensitive_home(monkeypatch) -> None:
    ssh = Path(os.path.expanduser("~/.ssh"))
    monkeypatch.setattr(
        "backend.paths.is_sensitive_path",
        lambda path_str, base_dir=None: True,
    )
    assert safe_project_dir(str(ssh) if ssh.exists() else os.path.expanduser("~")) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest extras/roblox-mvp/tests/test_paths.py -v --tb=short`

Expected: FAIL with `ModuleNotFoundError: backend.paths` (or `safe_project_dir` undefined).

- [ ] **Step 3: Write the implementation**

```python
# extras/roblox-mvp/backend/paths.py
from __future__ import annotations

import os
from pathlib import Path

from kiro_crew.security import is_sensitive_path


def safe_project_dir(raw: str) -> Path | None:
    """Return a resolved existing directory, or None if unusable.

    Absoluteness is checked on the expanduser'd string BEFORE realpath, so a
    relative value cannot become absolute by accident (same contract as
    Spec Builder's ``_safe_dir``).
    """
    if not raw or not raw.strip():
        return None
    expanded = os.path.expanduser(raw.strip())
    if not os.path.isabs(expanded):
        return None
    resolved = Path(os.path.realpath(expanded))
    if is_sensitive_path(str(resolved)):
        return None
    if not resolved.is_dir():
        return None
    return resolved
```

```python
# extras/roblox-mvp/backend/__init__.py
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest extras/roblox-mvp/tests/test_paths.py -v --tb=short`

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add extras/roblox-mvp/backend extras/roblox-mvp/tests
git commit -m "feat(roblox-mvp): add project-dir validation"
```

---

### Task 2: Native folder picker

**Files:**
- Create: `extras/roblox-mvp/backend/picker.py`
- Test: `extras/roblox-mvp/tests/test_picker.py`

**Interfaces:**
- Consumes: `platform_compat.trusted_system_bin(name: str) -> str | None`, `IS_WINDOWS`
- Produces:
  - `pick_folder_supported() -> bool`
  - `pick_folder_sync() -> str | None`  (path or None if cancelled)
  - `PickerError` with `.code: str` for 501/500

- [ ] **Step 1: Write the failing tests**

```python
# extras/roblox-mvp/tests/test_picker.py
from __future__ import annotations

import subprocess

import pytest

from backend import picker


def test_unsupported_when_not_win_or_mac(monkeypatch) -> None:
    monkeypatch.setattr(picker, "IS_WINDOWS", False)
    monkeypatch.setattr(picker.sys, "platform", "linux")
    assert picker.pick_folder_supported() is False
    with pytest.raises(picker.PickerError) as exc:
        picker.pick_folder_sync()
    assert exc.value.code == "folder_chooser_unsupported"


def test_windows_returns_path(monkeypatch) -> None:
    monkeypatch.setattr(picker, "IS_WINDOWS", True)
    monkeypatch.setattr(picker.sys, "platform", "win32")
    monkeypatch.setattr(picker, "trusted_system_bin", lambda name: r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")

    class Result:
        returncode = 0
        stdout = "D:\\games\\parkour\n"
        stderr = ""

    monkeypatch.setattr(picker.subprocess, "run", lambda *a, **k: Result())
    assert picker.pick_folder_sync() == r"D:\games\parkour"


def test_windows_cancel_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(picker, "IS_WINDOWS", True)
    monkeypatch.setattr(picker.sys, "platform", "win32")
    monkeypatch.setattr(picker, "trusted_system_bin", lambda name: r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")

    class Result:
        returncode = 1
        stdout = ""
        stderr = "canceled"

    monkeypatch.setattr(picker.subprocess, "run", lambda *a, **k: Result())
    assert picker.pick_folder_sync() is None


def test_macos_uses_osascript(monkeypatch) -> None:
    monkeypatch.setattr(picker, "IS_WINDOWS", False)
    monkeypatch.setattr(picker.sys, "platform", "darwin")
    monkeypatch.setattr(picker, "trusted_system_bin", lambda name: "/usr/bin/osascript")

    class Result:
        returncode = 0
        stdout = "/Users/dev/game/\n"
        stderr = ""

    monkeypatch.setattr(picker.subprocess, "run", lambda *a, **k: Result())
    assert picker.pick_folder_sync() == "/Users/dev/game"


def test_missing_binary_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(picker, "IS_WINDOWS", True)
    monkeypatch.setattr(picker.sys, "platform", "win32")
    monkeypatch.setattr(picker, "trusted_system_bin", lambda name: None)
    with pytest.raises(picker.PickerError) as exc:
        picker.pick_folder_sync()
    assert exc.value.code == "picker_unavailable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest extras/roblox-mvp/tests/test_picker.py -v --tb=short`

Expected: FAIL with `ModuleNotFoundError: backend.picker`.

- [ ] **Step 3: Write the implementation**

```python
# extras/roblox-mvp/backend/picker.py
from __future__ import annotations

import subprocess
import sys

from kiro_crew.platform_compat import IS_WINDOWS, trusted_system_bin

_PICK_TIMEOUT_SEC = 180

_WIN_SCRIPT = (
    "Add-Type -AssemblyName System.Windows.Forms; "
    "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
    "$d.Description = 'Select project folder'; "
    "$d.ShowNewFolderButton = $false; "
    "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
    "Write-Output $d.SelectedPath } else { exit 1 }"
)

_MAC_SCRIPT = (
    'tell application "System Events" to activate\n'
    'POSIX path of (choose folder with prompt "Select project folder")'
)


class PickerError(Exception):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def pick_folder_supported() -> bool:
    return IS_WINDOWS or sys.platform == "darwin"


def pick_folder_sync() -> str | None:
    """Open the OS folder dialog. None = cancelled. Raises PickerError otherwise."""
    if not pick_folder_supported():
        raise PickerError("folder chooser is not available on this host", "folder_chooser_unsupported")
    if IS_WINDOWS:
        exe = trusted_system_bin("powershell")
        if not exe:
            raise PickerError("powershell is not available", "picker_unavailable")
        argv = [exe, "-NoProfile", "-STA", "-Command", _WIN_SCRIPT]
    else:
        exe = trusted_system_bin("osascript")
        if not exe:
            raise PickerError("osascript is not available", "picker_unavailable")
        argv = [exe, "-e", _MAC_SCRIPT]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=_PICK_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PickerError("folder chooser timed out", "picker_timeout") from exc
    if result.returncode != 0:
        err = (result.stderr or "").strip().lower()
        if "cancel" in err or result.returncode == 1:
            return None
        raise PickerError(err[-200:] or "folder chooser failed", "folder_chooser_failed")
    path = (result.stdout or "").strip().rstrip("/\\")
    return path or None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest extras/roblox-mvp/tests/test_picker.py extras/roblox-mvp/tests/test_paths.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extras/roblox-mvp/backend/picker.py extras/roblox-mvp/tests/test_picker.py
git commit -m "feat(roblox-mvp): add windows and macos folder picker"
```

---

### Task 3: Seed prompt and start-session

**Files:**
- Create: `extras/roblox-mvp/backend/session.py`
- Test: `extras/roblox-mvp/tests/test_session.py`

**Interfaces:**
- Consumes: `safe_project_dir(raw: str) -> Path | None`
- Produces:
  - `APP_NAME = "roblox-mvp"`
  - `PLANNER_AGENT = "roblox-mvp-spec"`
  - `DOC_FILES = ("gameplay.md", "levels.md", "acceptance.md")`
  - `seed_prompt(project_dir: Path) -> str`
  - `start_planner_session(state, project_dir: Path) -> dict` with keys
    `slot` (str) and `project_dir` (str). Calls
    `state.get_or_create_slot(agent=PLANNER_AGENT, app=APP_NAME)` then
    `dispatch_seed_turn(state, slot, seed)`.
  - `dispatch_seed_turn(state, slot, message: str) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# extras/roblox-mvp/tests/test_session.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest extras/roblox-mvp/tests/test_session.py -v --tb=short`

Expected: FAIL with `ModuleNotFoundError: backend.session`.

- [ ] **Step 3: Write the implementation**

```python
# extras/roblox-mvp/backend/session.py
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
    asyncio.get_running_loop().create_task(bounded_chat_turn(_run_chat(state, slot, message)))


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest extras/roblox-mvp/tests/test_session.py extras/roblox-mvp/tests/test_paths.py extras/roblox-mvp/tests/test_picker.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extras/roblox-mvp/backend/session.py extras/roblox-mvp/tests/test_session.py
git commit -m "feat(roblox-mvp): seed planner session with project dir"
```

---

### Task 4: HTTP routes

**Files:**
- Create: `extras/roblox-mvp/backend/routes.py`
- Test: `extras/roblox-mvp/tests/test_routes.py`

**Interfaces:**
- Consumes: `safe_project_dir`, `pick_folder_sync`, `PickerError`, `start_planner_session`
- Produces: `register_routes(ctx) -> list[AppRoute]` with
  `POST /pick-folder` and `POST /start`
- Handler signature: `async def handler(request: web.Request, ctx: AppContext) -> web.Response`

- [ ] **Step 1: Write the failing tests**

```python
# extras/roblox-mvp/tests/test_routes.py
from __future__ import annotations

import json
from pathlib import Path

from aiohttp.test_utils import make_mocked_request

from kiro_crew.apps.context import AppContext
from kiro_crew.apps.route_registry import AppRoute
from backend.routes import register_routes


def _ctx(tmp_path: Path) -> AppContext:
    return AppContext(name="roblox-mvp", data_dir=tmp_path)


def test_register_routes_lists_pick_and_start(tmp_path: Path) -> None:
    routes = register_routes(_ctx(tmp_path))
    pairs = {(r.method, r.path) for r in routes}
    assert ( "POST", "/pick-folder") in pairs
    assert ("POST", "/start") in pairs
    assert all(isinstance(r, AppRoute) for r in routes)


async def test_start_rejects_relative_path(tmp_path: Path) -> None:
    routes = {r.path: r for r in register_routes(_ctx(tmp_path))}
    req = make_mocked_request("POST", "/api/apps/roblox-mvp/start")
    req._read_bytes = json.dumps({"project_dir": "relative"}).encode()
    resp = await routes["/start"].handler(req, _ctx(tmp_path))
    assert resp.status == 400
    body = json.loads(resp.text)
    assert body["code"] == "invalid_project_dir"
```

If `make_mocked_request` plus `_read_bytes` is awkward on this aiohttp version,
construct the handler test by calling an extracted `parse_start_body` /
`start_response(project_dir, state)` instead — keep the 400 `code` assertion.

Add tests:

- `POST /start` with `tmp_path` and a stub `request.app["state"]` returns 201
  and `{"slot": "...", "project_dir": ...}`.
- `POST /pick-folder` when `pick_folder_sync` raises `PickerError(code="folder_chooser_unsupported")`
  returns 501 with that `code`.
- `POST /pick-folder` when sync returns `None` returns 200 `{"cancelled": true, "path": null}`.
- `POST /pick-folder` when already in progress (module lock) returns 409
  `{"code": "picker_busy"}`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest extras/roblox-mvp/tests/test_routes.py -v --tb=short`

Expected: FAIL with `ModuleNotFoundError: backend.routes`.

- [ ] **Step 3: Write the implementation**

```python
# extras/roblox-mvp/backend/routes.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest extras/roblox-mvp/tests -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extras/roblox-mvp/backend/routes.py extras/roblox-mvp/tests/test_routes.py
git commit -m "feat(roblox-mvp): add pick-folder and start routes"
```

---

### Task 5: Agent templates, prompts, and skills

**Files:**
- Create: `extras/roblox-mvp/agents/roblox-mvp-spec.json`
- Create: `extras/roblox-mvp/agents/roblox-mvp-builder.json`
- Create: `extras/roblox-mvp/prompts/spec.md`
- Create: `extras/roblox-mvp/prompts/builder.md`
- Create: `extras/roblox-mvp/skills/roblox-mvp-docs/SKILL.md`
- Create: `extras/roblox-mvp/skills/roblox-studio-draft/SKILL.md`
- Create: `extras/roblox-mvp/skills/roblox-mvp-build/SKILL.md`
- Test: `extras/roblox-mvp/tests/test_agents.py`

**Interfaces:**
- Produces: two agent JSON files whose `name`, `tools`, `mcpServers`, and
  `toolsSettings.subagent` match the spec. Prompts are `file://` relative
  resources resolved at install (use prompt strings in JSON if `file://`
  placeholders are not rendered for local apps — prefer inline `prompt`
  text that matches `prompts/*.md` so tests can read either).

Put the full planner/builder prompt text in `prompts/*.md` and set each
agent's `"prompt"` to that file's contents copied at authoring time, **or**
`"prompt": "file://prompts/spec.md"` if the App Kit agent materializer
resolves relative `file://` the same way PPTX Maker does with `{APP_}`
placeholders. For a local app with no provision step, **inline the prompt
string in the JSON** (read from the md file in the test to keep them equal).

- [ ] **Step 1: Write the failing tests**

```python
# extras/roblox-mvp/tests/test_agents.py
from __future__ import annotations

import json
from pathlib import Path

_APP = Path(__file__).resolve().parents[1]


def _agent(name: str) -> dict:
    return json.loads((_APP / "agents" / f"{name}.json").read_text(encoding="utf-8"))


def test_planner_has_no_studio_and_can_spawn_builder() -> None:
    spec = _agent("roblox-mvp-spec")
    tools = spec["tools"]
    assert spec["model"] == "auto"
    assert spec["name"] == "roblox-mvp-spec"
    assert "use_subagent" in tools
    assert all("@roblox-studio" not in t for t in tools)
    assert "mcpServers" not in spec
    sub = spec["toolsSettings"]["subagent"]
    assert sub["availableAgents"] == ["roblox-mvp-builder"]
    assert sub["trustedAgents"] == ["roblox-mvp-builder"]
    blob = spec["prompt"] + (_APP / "prompts" / "spec.md").read_text(encoding="utf-8")
    assert "确认" in blob
    assert "use_subagent" in blob or "roblox-mvp-builder" in blob


def test_builder_has_no_subagent_and_no_destructive_tools() -> None:
    builder = _agent("roblox-mvp-builder")
    tools = builder["tools"]
    assert builder["model"] == "auto"
    assert builder["name"] == "roblox-mvp-builder"
    assert "use_subagent" not in tools
    joined = " ".join(tools).lower()
    assert "publish" not in joined
    assert "commit" not in joined
    assert "delete" not in joined
    assert "read" in tools and "glob" in tools and "grep" in tools
    assert "roblox-studio" in builder["mcpServers"]
    assert "mcpServers" in builder
```

Also assert the three `SKILL.md` files exist and contain:

- docs: `PROJECT_DIR`, `gameplay.md`, `levels.md`, `acceptance.md`
- draft: 草稿, 不提交, 不发布, 变更表
- build: Place, 只实现文档里有的

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest extras/roblox-mvp/tests/test_agents.py -v --tb=short`

Expected: FAIL (files missing).

- [ ] **Step 3: Write the files**

Planner JSON (tools exactly as specified):

```json
{
  "name": "roblox-mvp-spec",
  "description": "Writes Roblox MVP docs, then spawns the builder after confirmation.",
  "model": "auto",
  "prompt": "<paste prompts/spec.md>",
  "resources": ["file://skills/roblox-mvp-docs/SKILL.md"],
  "tools": ["read", "write", "glob", "grep", "use_subagent"],
  "toolsSettings": {
    "subagent": {
      "availableAgents": ["roblox-mvp-builder"],
      "trustedAgents": ["roblox-mvp-builder"]
    }
  },
  "welcomeMessage": "先用开始页选文件夹。选好后在这里聊玩法，确认前不会写 Studio。"
}
```

Builder JSON:

```json
{
  "name": "roblox-mvp-builder",
  "description": "Drafts the confirmed MVP into the connected Roblox Studio place.",
  "model": "auto",
  "prompt": "<paste prompts/builder.md>",
  "resources": [
    "file://skills/roblox-studio-draft/SKILL.md",
    "file://skills/roblox-mvp-build/SKILL.md"
  ],
  "mcpServers": {
    "roblox-studio": {
      "command": "npx",
      "args": ["-y", "roblox-studio-mcp"]
    }
  },
  "tools": ["read", "glob", "grep"]
}
```

Leave Studio tool names off the allowlist until the department's MCP
`tools/list` is known. Connecting the server without listing its tools
hides them from the model (App Kit: no `@server` ref → tools hidden).
After the department supplies the real command and tool names, add only
read/write-draft tools as `@roblox-studio/<name>` in the same commit that
updates `command`/`args`. Do not add publish/commit/delete names.

`prompts/spec.md` must include: seed `PROJECT_DIR` is the only write
root; three filenames; one mechanic / one scene; stop after writing;
spawn `roblox-mvp-builder` only on explicit confirmation; no Studio
tools.

`prompts/builder.md` must include: read the three files first; stop on
gaps; identify Place before write; drafts only; on MCP failure stop and
do not edit markdown; Place loses to confirmed docs; end with a change
table; do not claim Play passed.

Skill bodies match the spec table. Frontmatter:

```markdown
---
name: roblox-mvp-docs
description: "Write gameplay.md, levels.md, and acceptance.md for a one-mechanic Roblox MVP. Load in the roblox-mvp-spec planner session."
---
```

(and analogous for the two builder skills.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest extras/roblox-mvp/tests/test_agents.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extras/roblox-mvp/agents extras/roblox-mvp/prompts extras/roblox-mvp/skills extras/roblox-mvp/tests/test_agents.py
git commit -m "feat(roblox-mvp): add planner and builder agent templates"
```

---

### Task 6: Manifest, start page, and install README

**Files:**
- Create: `extras/roblox-mvp/app.json`
- Create: `extras/roblox-mvp/README.md`
- Create: `extras/roblox-mvp/ui/package.json`
- Create: `extras/roblox-mvp/ui/vite.config.ts`
- Create: `extras/roblox-mvp/ui/tsconfig.json`
- Create: `extras/roblox-mvp/ui/src/App.tsx`
- Create: `extras/roblox-mvp/ui/.gitignore` (`node_modules/`)
- Modify: `docs/superpowers/plans/README.md` (add this plan if not already listed)
- Test: `extras/roblox-mvp/tests/test_manifest.py`

**Interfaces:**
- Consumes: routes and agents from earlier tasks
- Produces: an installable local app

- [ ] **Step 1: Write the failing manifest test**

```python
# extras/roblox-mvp/tests/test_manifest.py
from __future__ import annotations

import json
from pathlib import Path

_APP = Path(__file__).resolve().parents[1]


def test_manifest_is_local_app_with_two_agents() -> None:
    man = json.loads((_APP / "app.json").read_text(encoding="utf-8"))
    assert man["name"] == "roblox-mvp"
    assert man["defaultEnabled"] is False
    assert "agents/roblox-mvp-spec.json" in man["agents"]
    assert "agents/roblox-mvp-builder.json" in man["agents"]
    assert man["backend"]["hooks"]["routes"] == "backend.routes:register_routes"
    assert man["ui"]["entry"] == "dist/index.mjs"
    assert "/api/apps/roblox-mvp" in man["permissions"]["api"]
    assert "/api/chat" in man["permissions"]["api"]
    assert ( _APP / "ui" / "src" / "App.tsx").is_file()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest extras/roblox-mvp/tests/test_manifest.py -v --tb=short`

Expected: FAIL (app.json missing).

- [ ] **Step 3: Write app.json, UI, and README**

`app.json`:

```json
{
  "name": "roblox-mvp",
  "version": "0.1.0",
  "displayName": "Roblox MVP",
  "description": "对话写出玩法文档，确认后用 Studio MCP 搭一份可 Play 的草稿。",
  "author": "kirocrew",
  "defaultEnabled": false,
  "agents": [
    "agents/roblox-mvp-spec.json",
    "agents/roblox-mvp-builder.json"
  ],
  "skills": [
    "skills/roblox-mvp-docs",
    "skills/roblox-studio-draft",
    "skills/roblox-mvp-build"
  ],
  "mcpServers": {
    "roblox-studio": {
      "command": "npx",
      "args": ["-y", "roblox-studio-mcp"]
    }
  },
  "permissions": {
    "api": [
      "/api/apps/roblox-mvp",
      "/api/apps/roblox-mvp/*",
      "/api/chat",
      "/api/chat/*"
    ],
    "storage": true
  },
  "backend": {
    "hooks": {
      "routes": "backend.routes:register_routes"
    }
  },
  "ui": {
    "entry": "dist/index.mjs",
    "pages": [
      {
        "route": "/roblox-mvp",
        "label": "Roblox MVP",
        "icon": "Gamepad2"
      }
    ]
  },
  "platform": {
    "os": ["windows", "macos", "linux"]
  }
}
```

`ui/vite.config.ts` — library build, externals:
`react`, `react-dom`, `lucide-react`, `@kirocrew/app-sdk`,
`@kirocrew/app-sdk/ui`. Output `dist/index.mjs`.

`ui/src/App.tsx`:

- `PageHeader` title `Roblox MVP`.
- Path `Input` (always visible).
- `Btn`「选择文件夹」→ `POST /api/apps/roblox-mvp/pick-folder`. On
  `path`, set the field. On `cancelled`, clear status. On 501/4xx, show
  `error` and keep the field.
- `Btn`「开始」disabled when the field is empty or not absolute
  (`/`, `\\`, or `^[A-Za-z]:[\\/]`).
- 「开始」→ `POST /api/apps/roblox-mvp/start` with `{ project_dir }`.
  On 201, `useNavigate()('/chat?slot=' + encodeURIComponent(data.slot))`.
- Use `useAppApi` and `useNavigate` from `@kirocrew/app-sdk`.
- `Btn` / `Input` / `PageHeader` from `@kirocrew/app-sdk/ui`.
- No `useEffect`+`useState` fetch pattern for listing; React Query is
  not required for two button clicks. Local component state for the
  path string and an error string is enough.

`README.md` (Chinese + commands):

```
kirocrew app install extras/roblox-mvp
# build UI first: cd extras/roblox-mvp/ui && npm install && npm run build
kirocrew app enable roblox-mvp
```

State that `mcpServers.roblox-studio.command` must be replaced with the
department's real Studio MCP launch spec before the builder can write a
Place. Studio must be open. Tests:

`python -m pytest extras/roblox-mvp/tests -v --tb=short`

- [ ] **Step 4: Run tests and the UI build**

Run:

```
python -m pytest extras/roblox-mvp/tests -v --tb=short
cd extras/roblox-mvp/ui && npm install && npm run build
```

Expected: pytest PASS; `extras/roblox-mvp/ui/dist/index.mjs` exists.

- [ ] **Step 5: Commit**

```bash
git add extras/roblox-mvp docs/superpowers/plans/README.md
git commit -m "feat(roblox-mvp): add manifest, start page, and install readme"
```

Do not commit `ui/node_modules`. Commit `ui/dist/index.mjs` if the
install path expects a prebuilt bundle; otherwise document `npm run build`
as a required install step and gitignore `dist/` — pick **gitignore
`ui/dist` and `ui/node_modules`**, require build before install (matches
the full-app example).

---

## Self-review (spec coverage)

| Spec section | Task |
|---|---|
| Local app at `extras/roblox-mvp/`, not builtin | 6 |
| Start page: choose / type / start | 6 |
| Native dialog Windows + macOS, typed fallback | 2, 4, 6 |
| Path absolute + exists + not sensitive | 1, 4 |
| Seed `PROJECT_DIR` + three filenames | 3 |
| Planner no Studio tools; trusted builder spawn | 5 |
| Builder no `use_subagent`; draft-only allowlist | 5 |
| Three docs + three skills | 5 |
| Studio MCP on builder / app only | 5, 6 |
| Confirm before spawn | 5 (prompt + skill) |
| Human Play; no auto Play | 5 (builder prompt) |
| Tests listed in spec | 1–6 |
| Later items (review page, two Places, …) | not scheduled |

No TBD left in this plan. Studio tool names stay off the allowlist until
the department fills `command`/`args` and a `tools/list`; that is an
explicit fail-closed choice, not an open placeholder.
