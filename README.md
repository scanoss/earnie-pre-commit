# Earnie pre-commit hook

This repository is a `pre-commit` wrapper around a **pinned** signed Earnie CLI
release. It downloads that exact CLI, verifies its SHA-256, and runs:

```sh
earnie scan staged --format hook
```

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

## Configuration

pre-commit appends `args` to the hook entry. This wrapper forwards those
arguments to the pinned CLI and keeps `--format hook` last, so the hook
identity cannot be overridden. Environment variables are inherited. Do not put
API keys in `.pre-commit-config.yaml`.

```yaml
repos:
  - repo: https://github.com/scanoss/earnie-pre-commit
    rev: v0.1.1
    hooks:
      - id: earnie
        args: ["--project", "billing", "--quiet"]
```

| Mechanism | Purpose |
| --- | --- |
| `args: ["--project", "<slug-or-uuid>"]` | Pin the Project when git remotes are unbound or a repo maps to more than one Project. Beats `EARNIE_PROJECT`, which beats the git remote |
| `args: ["--api-url", "<url>"]` or `EARNIE_API_URL` | Tenant URL, including CI machines without `~/.config/earnie` |
| `EARNIE_API_KEY` | CI only. Never commit it. Locally use `earnie auth login` / the OS keychain |
| `EARNIE_HOOK_FAIL_CLOSED=1` | Local stricter-only override. The Project setting is the real control |
| `args: ["--quiet"]`, `["--color", "never"]`, `["--no-update-check"]` | Reduce log noise |
| `EARNIE_PRE_COMMIT_CACHE` | Directory for the downloaded pinned binary |
| `SKIP=earnie`, `stages`, `rev` | pre-commit built-ins |

Leave these alone:

| Must stay fixed | Why |
| --- | --- |
| `scan staged --format hook` | That command is the hook. `--format` in `args` is ignored because the wrapper appends `--format hook` last |
| `--json`, `--no-wait` | The CLI rejects both with hook format |
| CLI version | Pin `rev` to a wrapper tag. The lockfile inside that tag is the CLI pin |

`--timeout` on `scan staged` does not change the hook wait bound (60s). Use
the Project fail-closed setting, not a longer local wait, when a scan must not
fail open.

Native Git hook without the pre-commit framework: `earnie hook install`. That
path does not take these `args`; set environment variables instead.

## Details

- Platforms: Linux and macOS amd64/arm64, Windows amd64.
- Cache: `~/.cache/earnie-pre-commit/` (or `%LOCALAPPDATA%\earnie-pre-commit\` on
  Windows). Override with `EARNIE_PRE_COMMIT_CACHE`.

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
