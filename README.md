# Earnie pre-commit hook

This repository is a `pre-commit` wrapper around a **pinned** signed Earnie CLI
release. It downloads that exact CLI, verifies its SHA-256, and runs:

```sh
earnie scan staged --format hook
```

It does not ship Earnie source. The CLI itself comes from
[scanoss/earnie-cli](https://github.com/scanoss/earnie-cli/releases).

## Quick path

1. Install and authenticate the Earnie CLI once (`earnie auth login`), or let
   this hook download the pinned CLI into a cache on first use.
2. Add the hook:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/scanoss/earnie-pre-commit
    rev: v0.1.1
    hooks:
      - id: earnie
```

3. Install environments **before the first commit**, so a download failure is
   not hidden inside a later hook run:

```sh
pre-commit install --install-hooks
pre-commit run earnie
```

`pre-commit run earnie` acquires and verifies CLI **0.1.1**. After that, every
commit scans the Git index.

## What it does

| Topic | Behaviour |
| --- | --- |
| Command | `earnie scan staged --format hook` |
| Files | Git index (ACMR), not the working tree |
| Pin | This revision downloads only CLI 0.1.1 with the release checksums |
| `block` | Exit 1, commit stopped |
| `require` | Exit 0 with an approval notice |
| Technical failure | Fail-open unless the Project sets fail-closed, or `EARNIE_HOOK_FAIL_CLOSED=1` |

## Details

- Platforms: Linux and macOS amd64/arm64, Windows amd64.
- Cache: `~/.cache/earnie-pre-commit/` (or `%LOCALAPPDATA%\earnie-pre-commit\` on
  Windows). Override with `EARNIE_PRE_COMMIT_CACHE`.
- Auth, API URL, and Project selection are the same as the normal CLI
  (`earnie auth login`, `EARNIE_API_URL`, `EARNIE_PROJECT`).
- Native Git hook without the pre-commit framework: `earnie hook install`.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| First run downloads slowly or fails | Run `pre-commit install --install-hooks` then `pre-commit run earnie` on a network that can reach GitHub Releases |
| `checksum mismatch` | Do not ignore it. This revision is pinned; open an issue rather than swapping the binary |
| Auth / network notice, commit still allowed | Default fail-open. Set fail-closed on the Project, or `EARNIE_HOOK_FAIL_CLOSED=1` locally to block |
| Another tool already owns `.git/hooks/pre-commit` | Use this repo's `.pre-commit-config.yaml` entry, or add `earnie scan staged --format hook` to that hook |

## Maintainers

Bump `src/earnie_pre_commit/release-lock.json` and `pyproject.toml` to a new
public CLI version, keep the hashes identical to that release's
`checksums.txt`, then tag `vX.Y.Z` to match. Consumers pin `rev` to that tag.
Do not move a published tag.
