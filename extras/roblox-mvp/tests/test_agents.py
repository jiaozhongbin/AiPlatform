from __future__ import annotations

import json
from pathlib import Path

_APP = Path(__file__).resolve().parents[1]

_PLANNER_PHRASES = (
    "确认",
    "PROJECT_DIR",
    "gameplay.md",
    "levels.md",
    "acceptance.md",
    "roblox-mvp-builder",
    "one mechanic",
    "one scene",
    "no Studio tools",
)

_BUILDER_PHRASES = (
    "read the three files first",
    "gaps",
    "identify Place",
    "drafts only",
    "do not edit the markdown",
    "Place loses to",
    "变更表",
    "do not claim Play passed",
)


def _agent(name: str) -> dict:
    return json.loads((_APP / "agents" / f"{name}.json").read_text(encoding="utf-8"))


def _assert_phrases_in_both(prompt: str, md: str, phrases: tuple[str, ...]) -> None:
    blob = prompt + md
    for phrase in phrases:
        assert phrase in blob
        assert phrase in prompt
        assert phrase in md


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


def test_planner_prompt_and_md_share_required_phrases() -> None:
    spec = _agent("roblox-mvp-spec")
    md = (_APP / "prompts" / "spec.md").read_text(encoding="utf-8")
    _assert_phrases_in_both(spec["prompt"], md, _PLANNER_PHRASES)
    assert spec["welcomeMessage"] == "先用开始页选文件夹。选好后在这里聊玩法，确认前不会写 Studio。"
    assert spec["resources"] == ["file://skills/roblox-mvp-docs/SKILL.md"]
    assert spec["tools"] == ["read", "write", "glob", "grep", "use_subagent"]
    assert not spec["prompt"].startswith("file://")


def test_builder_prompt_and_md_share_required_phrases() -> None:
    builder = _agent("roblox-mvp-builder")
    md = (_APP / "prompts" / "builder.md").read_text(encoding="utf-8")
    _assert_phrases_in_both(builder["prompt"], md, _BUILDER_PHRASES)
    assert builder["resources"] == [
        "file://skills/roblox-studio-draft/SKILL.md",
        "file://skills/roblox-mvp-build/SKILL.md",
    ]
    assert builder["tools"] == ["read", "glob", "grep"]
    assert builder["mcpServers"]["roblox-studio"]["command"] == "npx"
    assert builder["mcpServers"]["roblox-studio"]["args"] == ["-y", "roblox-studio-mcp"]
    assert not builder["prompt"].startswith("file://")
    assert all("@roblox-studio" not in t for t in builder["tools"])


def test_skill_files_exist_and_contain_required_phrases() -> None:
    docs = (_APP / "skills" / "roblox-mvp-docs" / "SKILL.md").read_text(encoding="utf-8")
    draft = (_APP / "skills" / "roblox-studio-draft" / "SKILL.md").read_text(encoding="utf-8")
    build = (_APP / "skills" / "roblox-mvp-build" / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("PROJECT_DIR", "gameplay.md", "levels.md", "acceptance.md"):
        assert phrase in docs
    for phrase in ("草稿", "不提交", "不发布", "变更表"):
        assert phrase in draft
    assert "Place" in build
    assert "只实现文档里有的" in build
    assert "name: roblox-mvp-docs" in docs
    assert "name: roblox-studio-draft" in draft
    assert "name: roblox-mvp-build" in build
