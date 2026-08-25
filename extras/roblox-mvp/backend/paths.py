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
