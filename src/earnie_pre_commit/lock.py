from __future__ import annotations

import json
import os
import platform
import sys
from importlib import resources
from typing import Any


SUPPORTED = (
    "darwin_amd64",
    "darwin_arm64",
    "linux_amd64",
    "linux_arm64",
    "windows_amd64",
)


def load_lock() -> dict[str, Any]:
    text = resources.files("earnie_pre_commit").joinpath("release-lock.json").read_text(encoding="utf-8")
    lock = json.loads(text)
    version = lock.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("release lock is missing version")
    archives = lock.get("archives")
    if not isinstance(archives, dict):
        raise ValueError("release lock is missing archives")
    for name in SUPPORTED:
        archive = archives.get(name)
        if not isinstance(archive, dict):
            raise ValueError(f"release lock is missing {name}")
        sha = archive.get("sha256")
        filename = archive.get("name")
        if not isinstance(filename, str) or not filename:
            raise ValueError(f"release lock {name} is missing name")
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError(f"release lock {name} has an invalid sha256")
    return lock


def current_platform(system: str | None = None, machine: str | None = None) -> str:
    system = (system or sys.platform).lower()
    machine = (machine or platform.machine()).lower()
    if system.startswith("linux"):
        os_name = "linux"
    elif system.startswith("darwin"):
        os_name = "darwin"
    elif system.startswith("win"):
        os_name = "windows"
    else:
        raise ValueError(f"unsupported operating system: {system}")
    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"aarch64", "arm64"}:
        arch = "arm64"
    else:
        raise ValueError(f"unsupported architecture: {machine}")
    name = f"{os_name}_{arch}"
    if name not in SUPPORTED:
        raise ValueError(f"unsupported platform: {name}")
    return name


def archive_for(lock: dict[str, Any], platform_name: str) -> dict[str, str]:
    archives = lock["archives"]
    archive = archives[platform_name]
    return {"name": archive["name"], "sha256": archive["sha256"]}


def cache_root() -> str:
    override = os.environ.get("EARNIE_PRE_COMMIT_CACHE")
    if override:
        return override
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "earnie-pre-commit")
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return os.path.join(xdg, "earnie-pre-commit")
    return os.path.join(os.path.expanduser("~"), ".cache", "earnie-pre-commit")
