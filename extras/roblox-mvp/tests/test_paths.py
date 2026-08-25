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
