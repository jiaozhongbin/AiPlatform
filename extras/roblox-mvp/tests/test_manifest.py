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
    assert (_APP / "ui" / "src" / "App.tsx").is_file()


def test_manifest_declares_skills_mcp_pages_and_platforms() -> None:
    man = json.loads((_APP / "app.json").read_text(encoding="utf-8"))
    assert man["skills"] == [
        "skills/roblox-mvp-docs",
        "skills/roblox-studio-draft",
        "skills/roblox-mvp-build",
    ]
    studio = man["mcpServers"]["roblox-studio"]
    assert studio["command"] == "npx"
    assert studio["args"] == ["-y", "roblox-studio-mcp"]
    assert "/api/apps/roblox-mvp/*" in man["permissions"]["api"]
    assert "/api/chat/*" in man["permissions"]["api"]
    pages = man["ui"]["pages"]
    assert pages[0]["route"] == "/roblox-mvp"
    assert pages[0]["label"] == "Roblox MVP"
    assert pages[0]["icon"] == "Gamepad2"
    assert man["platform"]["os"] == ["windows", "macos", "linux"]


def test_start_page_uses_sdk_and_chinese_copy() -> None:
    src = (_APP / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "PageHeader" in src
    assert "Roblox MVP" in src
    assert "选择文件夹" in src
    assert "开始" in src
    assert "/api/apps/roblox-mvp/pick-folder" in src
    assert "/api/apps/roblox-mvp/start" in src
    assert "useAppApi" in src
    assert "useNavigate" in src
    assert "from '@kirocrew/app-sdk'" in src
    assert "from '@kirocrew/app-sdk/ui'" in src
    assert "encodeURIComponent" in src
    vite = (_APP / "ui" / "vite.config.ts").read_text(encoding="utf-8")
    for name in (
        "react",
        "react-dom",
        "lucide-react",
        "@kirocrew/app-sdk",
        "@kirocrew/app-sdk/ui",
    ):
        assert name in vite
