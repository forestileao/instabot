# AGENTS.md

Guidance for coding agents working in this repository.

## TL;DR

- What it is: a small Python 3 Instagram automation bot (`InstaBot` class).
- What it does: logs into an account, then runs two background threads —
  one follows users, one unfollows people who don't follow you back.
- How to run it: `cd insta_bot && python3 main.py`
  (it MUST be run from inside `insta_bot/`, not the repo root).
- Where the logic lives: everything is in `insta_bot/src/insta_bot.py`.
- Config: `insta_bot/credentials.json` (never commit real credentials).
- Read the "Known issues" section before changing any bot logic.

## Project overview

Insta Bot v1.0.0 is a single-class Instagram automation tool. You give it an
Instagram login and, optionally, a target username. On start it:

1. Logs in (`login`).
2. Maps follower/following data into memory and JSON cache files.
3. Starts two threads (`start`):
   - `just_follow` — follows either the target user's followers (when a
     `target_username` is set) or Instagram's "suggested" users.
   - `just_unfollow` — unfollows accounts you follow that don't follow back.

There is no official Instagram API and no browser automation. The bot calls
Instagram's private ajax/GraphQL endpoints directly with `requests`, using
hardcoded `query_hash` values. This approach is fragile (see Known issues).

## Tech stack

- Language: Python 3 (3.11 is available here; no version is pinned).
- Only third-party dependency: `requests~=2.24.0` (declared in `setup.py`).
- Standard library used: `json`, `threading.Thread`, `time`/`time.sleep`,
  `os.path`.
- No tests, no linter, no CI exist in this repo.

## Repository layout

```
setup.py                        Package metadata; installs insta_bot + requests
README.md                       Human-facing install/usage notes
.gitignore                      Ignores egg-info, __pycache__, venv, cache JSON
insta_bot/
  __init__.py                   Empty
  main.py                       Entrypoint (reads ./credentials.json, runs bot)
  credentials.json              Config file (placeholder values are committed)
  src/
    __init__.py                 Empty
    insta_bot.py                The entire implementation (InstaBot class)
  cache/
    .gitkeep                    Keeps the folder tracked in git
    *.json                      Runtime output (followers/following/target)
```

## Setup

```sh
python3 -m venv venv
source venv/bin/activate
pip3 install -e .
```

This installs the `insta_bot` package and its one dependency, `requests`.

## Configuration

Before running, put real values in `insta_bot/credentials.json`:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": ""
}
```

- `username` / `password`: the account the bot logs in as.
- `target_username`: optional.
  - Empty string `""` (the committed default): the bot follows Instagram's
    suggested users.
  - A username (e.g. `"john.doe"`): the bot follows that user's followers.

Never commit real credentials. The committed `credentials.json` holds
placeholders only — keep it that way and treat any local edits with real
secrets as local-only, untracked changes.

## Running

```sh
cd insta_bot
python3 main.py
```

Why the `cd` matters: `main.py` does `from src.insta_bot import InstaBot` and
opens `./credentials.json` by relative path. Both only resolve when the
current directory is `insta_bot/`. Running `python3 insta_bot/main.py` from
the repo root fails with an import error and/or a missing-file error.

## Coding conventions

When editing `insta_bot/src/insta_bot.py`, match the existing style:

- 4-space indentation; `snake_case` for methods and variables.
- Use f-strings for formatting.
- Logging is print-based, not the `logging` module. Existing prefixes:
  - `>` for per-item/status lines.
  - `***` for section banners, e.g. `*** Mapping followers ***`.
- Keep extra per-user output behind the `verbose` flag (passed via `start`).
- `InstaBot` is the only abstraction — there are no helper modules, config
  objects, or other classes.

## Cache files

At runtime the bot writes JSON into `insta_bot/cache/`:

- `followers.json` — your own followers.
- `following.json` — accounts you follow.
- `target-followers.json` — the target user's followers.

These are generated at runtime and are gitignored (except `.gitkeep`, which
keeps the directory in version control). But note the `.gitignore` typo in
Known issues below.

## Testing / linting

None exist today. If you add tests or a linter, you are setting up the
tooling from scratch — there is no existing convention to follow.

## Known issues / gotchas

These are existing quirks in the code. They are not required fixes for
documentation tasks, but they matter if you touch nearby logic:

- Fragile private API: the bot depends on undocumented Instagram endpoints
  and hardcoded `query_hash` values (`map_followers`, `map_user_followers`,
  `map_following`, `get_suggested_followers`). These break when Instagram
  changes its internal API, and such traffic is often rate-limited or blocked.
- Wrong list persisted: `map_user_followers` writes `self.followers` to
  `target-followers.json` instead of `self.user_followers` (likely a bug).
- `.gitignore` typo: it lists `target-followes.json` (missing an "r"), but
  the code writes `target-followers.json`, so that cache file is NOT ignored.
- Packaging gap: `setup.py` lists only `insta_bot` in `packages`, not
  `insta_bot.src`, so a non-editable install may miss the `src` subpackage.
- Silent failures: `just_follow` uses bare `except:` blocks that swallow all
  errors.
- Blocking sleeps: rate-limit handling is a blocking `sleep(10 * 60)` inside
  worker threads, with no backoff, cap, or graceful cancellation.
- Dead break in `just_unfollow`: `count` is reset to `1` at the top of each
  loop iteration, so the `count >= 50` break can never trigger.
