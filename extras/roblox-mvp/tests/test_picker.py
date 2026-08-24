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
