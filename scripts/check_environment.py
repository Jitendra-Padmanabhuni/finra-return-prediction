"""Report Phase 0 environment capabilities without modifying project data."""

from __future__ import annotations

import importlib
import platform
import sys


PACKAGES = ("numpy", "pandas", "scipy", "statsmodels", "matplotlib", "yaml", "pytest")


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    unavailable: list[str] = []
    for package in PACKAGES:
        try:
            module = importlib.import_module(package)
            version = getattr(module, "__version__", "available")
            print(f"{package}: {version}")
        except Exception as exc:
            unavailable.append(package)
            print(f"{package}: unavailable ({type(exc).__name__}: {exc})")
    return 1 if unavailable else 0


if __name__ == "__main__":
    raise SystemExit(main())

