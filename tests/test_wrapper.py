from __future__ import annotations

import io
import os
import pathlib
import tarfile
import tempfile
import unittest
from unittest import mock

from earnie_pre_commit.lock import SUPPORTED, archive_for, current_platform, load_lock


class LockTests(unittest.TestCase):
    def test_lock_pins_cli_0_1_1_with_five_archives(self):
        lock = load_lock()
        self.assertEqual("0.1.1", lock["version"])
        self.assertEqual(
            "https://github.com/scanoss/earnie-cli/releases/download/v0.1.1",
            lock["release_base_url"],
        )
        self.assertEqual(set(SUPPORTED), set(lock["archives"]))
        for name in SUPPORTED:
            archive = archive_for(lock, name)
            self.assertIn(f"earnie_0.1.1_{name}.", archive["name"])
            self.assertEqual(64, len(archive["sha256"]))

    def test_current_platform_maps_common_names(self):
        self.assertEqual("linux_amd64", current_platform("linux", "x86_64"))
        self.assertEqual("linux_arm64", current_platform("linux", "aarch64"))
        self.assertEqual("darwin_arm64", current_platform("darwin", "arm64"))
        self.assertEqual("darwin_amd64", current_platform("darwin", "amd64"))
        self.assertEqual("windows_amd64", current_platform("win32", "AMD64"))
        with self.assertRaises(ValueError):
            current_platform("linux", "riscv64")
        with self.assertRaises(ValueError):
            current_platform("freebsd", "amd64")


class ManifestTests(unittest.TestCase):
    def test_pre_commit_manifest_scans_the_whole_index(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        text = (root / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
        self.assertIn("id: earnie", text)
        self.assertIn("entry: earnie-pre-commit", text)
        self.assertIn("language: python", text)
        self.assertIn("pass_filenames: false", text)
        self.assertIn("always_run: true", text)
        self.assertIn("require_serial: true", text)
        self.assertIn("verbose: true", text)
        self.assertNotIn("language: system", text)


class AcquireTests(unittest.TestCase):
    def test_ensure_binary_verifies_checksum_and_extracts(self):
        from earnie_pre_commit.acquire import AcquireError, ensure_binary

        payload = _tar_gz_with_script("#!/bin/sh\necho ok\n")
        digest = _sha256(payload)
        lock = {
            "version": "0.1.1",
            "release_base_url": "http://example.test/v0.1.1",
            "archives": {
                "linux_amd64": {
                    "name": "earnie_0.1.1_linux_amd64.tar.gz",
                    "sha256": digest,
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = ensure_binary(
                lock=lock,
                platform_name="linux_amd64",
                cache_dir=directory,
                opener=_opener(payload),
            )
            self.assertTrue(os.access(path, os.X_OK))
            self.assertEqual(b"#!/bin/sh\necho ok\n", pathlib.Path(path).read_bytes())

            reused = ensure_binary(
                lock=lock,
                platform_name="linux_amd64",
                cache_dir=directory,
                opener=_opener(b"not-the-archive"),
            )
            self.assertEqual(path, reused)

        lock["archives"]["linux_amd64"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AcquireError) as caught:
                ensure_binary(
                    lock=lock,
                    platform_name="linux_amd64",
                    cache_dir=directory,
                    opener=_opener(payload),
                )
            self.assertIn("checksum mismatch", str(caught.exception))

    def test_hook_install_binary_prints_path(self):
        from earnie_pre_commit.hook import main

        with tempfile.TemporaryDirectory() as directory:
            fake = pathlib.Path(directory) / "earnie"
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            with mock.patch("earnie_pre_commit.hook.ensure_binary", return_value=str(fake)):
                self.assertEqual(0, main(["--install-binary"]))

    def test_hook_execs_scan_staged_format_hook(self):
        from earnie_pre_commit import hook as hook_mod

        with tempfile.TemporaryDirectory() as directory:
            fake = pathlib.Path(directory) / "earnie"
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            with mock.patch.object(hook_mod, "ensure_binary", return_value=str(fake)):
                with mock.patch.object(hook_mod.os, "execv") as execv:
                    execv.side_effect = SystemExit(0)
                    with self.assertRaises(SystemExit):
                        hook_mod.main([])
            execv.assert_called_once_with(
                str(fake), [str(fake), "scan", "staged", "--format", "hook"]
            )

    def test_hook_forwards_pre_commit_args_before_format_hook(self):
        from earnie_pre_commit import hook as hook_mod

        with tempfile.TemporaryDirectory() as directory:
            fake = pathlib.Path(directory) / "earnie"
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            with mock.patch.object(hook_mod, "ensure_binary", return_value=str(fake)):
                with mock.patch.object(hook_mod.os, "execv") as execv:
                    execv.side_effect = SystemExit(0)
                    with self.assertRaises(SystemExit):
                        hook_mod.main(["--project", "billing", "--quiet"])
            execv.assert_called_once_with(
                str(fake),
                [
                    str(fake),
                    "scan",
                    "staged",
                    "--project",
                    "billing",
                    "--quiet",
                    "--format",
                    "hook",
                ],
            )


def _tar_gz_with_script(script: str) -> bytes:
    buffer = io.BytesIO()
    data = script.encode()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo(name="earnie")
        info.size = len(data)
        info.mode = 0o755
        archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _sha256(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _opener(payload: bytes):
    class Response:
        def read(self):
            return payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def open_url(_url: str):
        return Response()

    return open_url


if __name__ == "__main__":
    unittest.main()
