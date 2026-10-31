#!/usr/bin/env python3
"""Install NovaStack Mail CLI without reinstalling already-satisfied dependencies."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path

REQUIREMENTS = {
    "requests": ("requests", "2.25.0"),
    "rich": ("rich", "13.7.0"),
}


def installed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def version_at_least(actual: str, minimum: str) -> bool:
    # pip vendors packaging, so no extra installer dependency is required.
    from pip._vendor.packaging.version import Version
    return Version(actual) >= Version(minimum)


def main() -> int:
    missing_or_old = []
    for distribution, (package, minimum) in REQUIREMENTS.items():
        current = installed_version(distribution)
        if current is None:
            print(f"[missing] {distribution} (requires >= {minimum})")
            missing_or_old.append(f"{package}>={minimum}")
        elif not version_at_least(current, minimum):
            print(f"[outdated] {distribution} {current} (requires >= {minimum})")
            missing_or_old.append(f"{package}>={minimum}")
        else:
            print(f"[ready] {distribution} {current}")

    if missing_or_old:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", *missing_or_old
        ])
    else:
        print("All runtime libraries already satisfy the requirements.")

    package_dir = Path(__file__).resolve().parent
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--no-deps", str(package_dir)
    ])
    print("NovaStack Mail CLI installed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
