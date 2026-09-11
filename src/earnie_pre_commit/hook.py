from __future__ import annotations

import os
import sys

from earnie_pre_commit.acquire import AcquireError, ensure_binary


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        binary = ensure_binary()
    except (AcquireError, ValueError) as exc:
        print(f"Earnie pre-commit: {exc}", file=sys.stderr)
        return 1
    if args == ["--install-binary"]:
        print(binary)
        return 0
    os.execv(binary, [binary, "scan", "staged", "--format", "hook"])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
