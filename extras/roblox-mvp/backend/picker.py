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
