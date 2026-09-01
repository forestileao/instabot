# AGENTS.md

Guidance for coding agents working in this repository.

## Project overview

Insta Bot v1.0.0 is a small Python 3 Instagram automation bot. Given a target
username, it maps that user's followers, then runs two background threads:
one that follows users (either the target's followers or Instagram's
"suggested" users) and one that unfollows accounts you follow that don't
follow you back. All Instagram interaction is done by talking directly to
Instagram's private ajax/GraphQL endpoints with `requests` (there is no
official API usage and no browser automation).

## Tech stack

- Python 3 (3.11 available in this environment; no version pin enforced).
- Single runtime dependency: `requests~=2.24.0` (see `setup.py`).
- Standard library only otherwise: `json`, `threading.Thread`, `time.sleep`, `os.path`.
- No test framework, no linter, no CI configuration exist in this repo.

## Repository structure

```
setup.py                        Package metadata; installs `insta_bot` + requests
README.md                       Install/usage instructions (human-facing)
.gitignore                      Ignores egg-info, __pycache__, venv, and cache JSON files
insta_bot/
  __init__.py                   Empty
  main.py                       Entrypoint: reads ./credentials.json, builds InstaBot, calls start()
  credentials.json              Config: username, password, target_username (placeholder values checked in)
  src/
    __init__.py                 Empty
    insta_bot.py                Entire implementation: the InstaBot class
  cache/
    .gitkeep                    Keeps the directory tracked in git
    (followers.json, following.json, target-followers.json)  Generated at runtime, gitignored
```

## Setup

```sh
python3 -m venv venv
source venv/bin/activate
pip3 install -e .
```

This installs the `insta_bot` package and its only dependency, `requests`.

## Configuration

Edit `insta_bot/credentials.json` with real values before running:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "john.doe"
}
```

- `username` / `password`: the Instagram account the bot logs in as.
- `target_username`: optional; if non-empty, the bot follows that user's
  followers instead of Instagram's suggested users.

Never commit real credentials. The checked-in `credentials.json` only
contains placeholder values — keep it that way, and treat any local edits
with real secrets as untracked/local-only changes.

## Running

```sh
cd insta_bot
python3 main.py
```

`main.py` runs `from src.insta_bot import InstaBot` and opens the file at the
relative path `./credentials.json`, so it **must be run from inside the
`insta_bot/` directory**. Running `python3 insta_bot/main.py` from the repo
root will fail with an import error and/or a missing-file error.

## Conventions

Match the existing style when editing `insta_bot/src/insta_bot.py`:

- 4-space indentation, snake_case method and variable names.
- f-strings for string formatting.
- Print-based logging, not the `logging` module. Existing prefixes:
  `>` for per-item/status messages, `***` for section banners
  (e.g. `*** Mapping followers ***`).
- The `verbose` flag (passed through `start()`) gates extra per-user print
  statements; keep new noisy logging behind it.
- Methods on `InstaBot` are the only abstraction in the codebase — there are
  no helper modules, config objects, or classes beyond it.

## Caching

Runtime results are written as JSON to `insta_bot/cache/`:

- `followers.json` — your own followers.
- `following.json` — accounts you follow.
- `target-followers.json` — the target user's followers.

These files are generated at runtime and are gitignored (aside from the
tracked `.gitkeep` placeholder that keeps the directory in version control).

## Testing / linting

There is no test suite and no linter configured in this project today. If
you add either, you'll be introducing the tooling from scratch — there is no
existing convention to follow.

## Known issues / gotchas

Be aware of these existing quirks; they are not required fixes for
documentation-only tasks, but they matter if you're asked to change nearby
code:

- The bot relies on undocumented Instagram private endpoints and hardcoded
  `query_hash` values (see `map_followers`, `map_user_followers`,
  `map_following`, `get_suggested_followers`). These break whenever
  Instagram changes its internal API, and Instagram aggressively rate-limits
  or blocks this kind of traffic.
- `map_user_followers()` writes `self.followers` to `target-followers.json`
  instead of `self.user_followers` — likely a bug; the wrong list gets
  persisted.
- `.gitignore` lists `target-followes.json` (typo, missing an "r"), but the
  code writes `target-followers.json`. As written, that cache file is
  **not** actually ignored by git.
- `setup.py`'s `packages` list only includes `insta_bot`, not
  `insta_bot.src`, so an installed (non-editable) package may be missing the
  `src` subpackage.
- Broad bare `except:` blocks swallow all errors in `just_follow()`.
- Rate-limit handling is a blocking `sleep(10 * 60)` (10 minutes) inside
  worker threads, with no backoff, cap, or way to cancel it gracefully.
