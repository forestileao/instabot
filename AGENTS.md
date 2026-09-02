# AGENTS.md

Guidance for AI coding agents working in this repository.

## 1. Project overview

Insta Bot is a small Python 3 command-line tool that automates two Instagram
actions: it follows the followers of a chosen "target" account, and it
unfollows accounts you follow that don't follow you back. It works by
driving Instagram's undocumented web/GraphQL endpoints directly with HTTP
requests (there is no official API usage and no browser automation). Because
it depends on private endpoints, hardcoded `query_hash` values, and scraped
response shapes, it is inherently fragile and can break silently whenever
Instagram changes its web app.

## 2. Tech stack

- Language: Python 3.
- Dependencies: a single third-party library, `requests~=2.24.0` (pinned in
  `setup.py`). Do not assume newer `requests` features are available.
- Packaging: `setuptools`, installed in editable mode (`pip3 install -e .`).
  The distributed package is named `insta-bot`; the importable package is
  `insta_bot`.
- Concurrency: standard library `threading.Thread` only (two worker threads
  started from `InstaBot.start()`), no asyncio, no multiprocessing.
- No test framework, no linter/formatter, no CI configured in this repo.

## 3. Repository layout

```
setup.py                       # package metadata, install_requires
README.md                      # user-facing install/usage instructions
insta_bot/
  __init__.py
  main.py                      # entrypoint, reads credentials.json, runs the bot
  credentials.json              # username/password/target_username (do not commit real values)
  src/
    __init__.py
    insta_bot.py               # the InstaBot class: all bot logic lives here
  cache/
    .gitkeep                   # keeps the folder tracked; runtime JSON is gitignored
```

Important: `main.py` opens `./credentials.json` relative to the current
working directory (it does not resolve a path relative to the file itself,
and it imports `from src.insta_bot import InstaBot`, a path only valid when
`insta_bot/` is the working directory). As a result, `main.py` must be run
from inside the `insta_bot/` directory, not from the repo root.

`InstaBot` (in `insta_bot/src/insta_bot.py`) writes its runtime state to
JSON files under `insta_bot/cache/` using paths relative to the module
file (`path.dirname(__file__) + '/../cache/...'`):
- `cache/followers.json` — your own followers.
- `cache/following.json` — accounts you follow.
- `cache/target-followers.json` — followers of the target account.

## 4. Setup and running

```sh
# optional virtualenv
python3 -m venv venv
source venv/bin/activate

# install the package and its one dependency (requests)
pip3 install -e .

# fill in insta_bot/credentials.json with real values:
#   { "username": "...", "password": "...", "target_username": "..." }

# run from inside insta_bot/, since main.py resolves paths relative to CWD
cd insta_bot
python3 main.py
```

`InstaBot.start()` logs in, then spawns two threads: one runs
`just_follow()` (maps followers of either your own account or
`target_username`, then follows suggested/target users), the other runs
`just_unfollow()` (maps your followers and following, then unfollows
accounts that don't follow you back). Both loops run indefinitely and sleep
between retries when Instagram responses fail.

## 5. Conventions for agents

- Keep dependencies minimal. Do not add new libraries unless the task
  genuinely requires it; if you do add one, update `install_requires` in
  `setup.py` and mention it in the README.
- Match the existing style: 4-space indentation, a single `InstaBot` class
  holding all bot behavior as instance methods, plain `print()` logging
  (no logging framework), f-strings for message formatting.
- Cache/output files belong under `insta_bot/cache/` and are gitignored
  (only `cache/.gitkeep` is tracked). Never commit generated
  `followers.json`, `following.json`, or `target-followers.json`.
- Never commit real Instagram credentials. `insta_bot/credentials.json`
  should only ever contain placeholder values in version control.

## 6. Known issues / gotchas (flag, don't silently "fix" unless asked)

- `map_user_followers` dumps `self.followers` instead of
  `self.user_followers` when writing `cache/target-followers.json`
  (`insta_bot/src/insta_bot.py`, around line 102) — the target's followers
  cache file is actually populated with your own followers list.
- `just_follow` wraps its per-user follow loop in a bare `except:` that
  swallows all errors (including bugs), only logging "Error in suggested"
  and sleeping.
- `just_unfollow`'s throttling logic is broken: `count` is reset to `1` on
  every iteration of the inner `for` loop instead of being initialized once
  before the loop, so the `count >= 50` cap never actually engages as
  intended.
- GraphQL `query_hash` values and REST endpoint paths (e.g.
  `/graphql/query/?query_hash=...`, `/web/friendships/{id}/follow/`) are
  hardcoded and scraped from Instagram's web client; they can go stale or
  start returning different shapes without warning.
- `login()` has a typo in its failure message: `"Erron on login
  authentication"` (should be "Error").

## 7. Testing / verification

There are no automated tests in this repository. At minimum, verify changes
by import-checking the package:

```sh
python3 -c "import insta_bot.src.insta_bot"
```

Because the bot performs live, authenticated network calls against
Instagram, most behavior cannot be safely exercised in CI or by an
automated agent. When you change bot logic, manually run it against a real
account (or otherwise describe the manual verification you performed) and
note the steps taken in your PR/commit description.
