from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[1]


def test_register_routes_loads_via_spec_from_file_location() -> None:
    """Gateway enable uses load_app_module → spec_from_file_location, not tests/conftest.py."""
    saved_path = list(sys.path)
    backend_keys = [k for k in sys.modules if k == "backend" or k.startswith("backend.")]
    saved_backend = {k: sys.modules[k] for k in backend_keys}
    unique_name = "_kirocrew_app_roblox-mvp.backend.routes"
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != _APP_ROOT.resolve()]
    for key in backend_keys:
        del sys.modules[key]
    sys.modules.pop(unique_name, None)
    try:
        file_path = _APP_ROOT / "backend" / "routes.py"
        spec = importlib.util.spec_from_file_location(unique_name, str(file_path))
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module
        spec.loader.exec_module(module)
        assert callable(module.register_routes)
    finally:
        sys.modules.pop(unique_name, None)
        sys.path[:] = saved_path
        sys.modules.update(saved_backend)
