from __future__ import annotations

import hashlib
import io
import os
import stat
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable

from earnie_pre_commit.lock import archive_for, cache_root, current_platform, load_lock

Opener = Callable[[str], Any]


class AcquireError(RuntimeError):
    pass


def binary_name(platform_name: str) -> str:
    if platform_name.startswith("windows"):
        return "earnie.exe"
    return "earnie"


def ensure_binary(
    *,
    lock: dict[str, Any] | None = None,
    platform_name: str | None = None,
    cache_dir: str | None = None,
    opener: Opener | None = None,
) -> str:
    lock = lock or load_lock()
    platform_name = platform_name or current_platform()
    archive = archive_for(lock, platform_name)
    dest_dir = Path(cache_dir or cache_root()) / str(lock["version"]) / platform_name
    dest = dest_dir / binary_name(platform_name)
    if dest.is_file() and os.access(dest, os.X_OK):
        return str(dest)

    url = lock.get("release_base_url", "").rstrip("/") + "/" + archive["name"]
    opener = opener or urllib.request.urlopen
    try:
        with opener(url) as response:
            payload = response.read()
    except Exception as exc:  # noqa: BLE001 — surface download failures as hook output
        raise AcquireError(f"failed to download pinned Earnie CLI from {url}: {exc}") from exc

    digest = hashlib.sha256(payload).hexdigest()
    if digest != archive["sha256"]:
        raise AcquireError(
            f"checksum mismatch for {archive['name']}: expected {archive['sha256']}, got {digest}"
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted = _extract_binary(payload, archive["name"], binary_name(platform_name))
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(extracted)
    tmp.chmod(tmp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    tmp.replace(dest)
    return str(dest)


def _extract_binary(payload: bytes, archive_name: str, expected: str) -> bytes:
    buffer = io.BytesIO(payload)
    if archive_name.endswith(".zip"):
        with zipfile.ZipFile(buffer) as archive:
            names = archive.namelist()
            match = _choose_member(names, expected)
            if match is None:
                raise AcquireError(f"{archive_name} does not contain {expected}")
            return archive.read(match)
    with tarfile.open(fileobj=buffer, mode="r:gz") as archive:
        names = [member.name for member in archive.getmembers() if member.isfile()]
        match = _choose_member(names, expected)
        if match is None:
            raise AcquireError(f"{archive_name} does not contain {expected}")
        extracted = archive.extractfile(match)
        if extracted is None:
            raise AcquireError(f"{archive_name} member {match} could not be read")
        return extracted.read()


def _choose_member(names: list[str], expected: str) -> str | None:
    exact = [name for name in names if name == expected or name.endswith("/" + expected)]
    if exact:
        return exact[0]
    return None
