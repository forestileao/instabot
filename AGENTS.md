# AGENTS.md

Guidance for coding agents working in this repository.

## Project overview

`insta-bot` (v1.0.0) is a small Python 3 Instagram automation bot. It logs
into Instagram through its private web/GraphQL endpoints and then, in two
background threads, follows new accounts (either Instagram's suggested
users or the followers of a chosen `target_username`) and unfollows
accounts that don't follow back. There is no UI, no server, and no
database — it is a single script driven by a JSON credentials file.

## Tech stack

- Python 3 (3.11 available in this environment)
- Only runtime dependency: `requests~=2.24.0` (see `setup.py`)
- No web framework, no database, no build tooling
- No tests, no linter/formatter config, no CI

## Project structure

```
setup.py                       package metadata, installs requests
README.md                      usage instructions
.gitignore                     ignores *.egg*, __pycache__, venv,
                                followers.json, target-followes.json,
                                following.json (root-level names — see
                                Gotchas below)
insta_bot/                     the package
  __init__.py                  empty
  main.py                      entry point; reads credentials.json,
                                starts InstaBot
  credentials.json             placeholder creds (username/password/
                                target_username)
  cache/.gitkeep                output dir for mapped JSON files
  src/__init__.py               empty
  src/insta_bot.py              InstaBot class (all logic)
```

`InstaBot` public surface:

- `__init__(username, password)`
- `start(target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False)`
  — launches two background threads, one running `just_follow`, one
  running `just_unfollow`.

Internals: `login`, `get_userid`, `map_followers`, `map_following`,
`map_user_followers`, `follow_user`, `unfollow_user`,
`get_suggested_followers`, `just_follow`, `just_unfollow`.

## Setup

```
pip3 install -e .
```

(Prefer doing this inside a virtualenv.) This installs the single
dependency, `requests`.

## Running

```
cd insta_bot && python3 main.py
```

Important: `main.py` must be run from **inside** the `insta_bot/`
directory, not from the repo root. It uses the import
`from src.insta_bot import InstaBot`, which only resolves when `src/` is
a sibling of the current working directory.

## Configuration

Edit `insta_bot/credentials.json` before running:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": ""
}
```

- `username` / `password`: the Instagram account the bot logs in as.
- `target_username`: optional. If non-empty, the bot follows the
  followers of this account instead of Instagram's suggested users.

## Code conventions

- Follow PEP 8: 4-space indentation, `snake_case` for functions/methods.
- Keep `InstaBot` methods single-responsibility, mirroring the existing
  style (one method per concern: login, map followers, map following,
  follow, unfollow, etc.).
- Use `requests.Session` (`self.session`) for all HTTP calls, consistent
  with `login()`.
- Write JSON caches (followers/following/target-followers) to
  `insta_bot/cache/`, matching existing `map_*` methods.

## Testing / quality

There is currently no test suite, linter, or CI configured. If tests are
added in the future, place them under a `tests/` directory at the repo
root and run them with a standard runner (e.g. `pytest`). Do not add
tests or tooling as part of documentation-only changes.

## Security / safety notes

- Never commit real Instagram credentials. `insta_bot/credentials.json`
  currently only contains placeholder values — keep it that way in
  version control.
- The bot relies on undocumented Instagram private web/GraphQL endpoints
  and hard-coded `query_hash` values, which Instagram can change or break
  at any time without notice.
- Be mindful of rate limits: on a failed follow/unfollow request, the
  code sleeps for roughly 10 minutes before retrying (see `just_follow`
  and `just_unfollow` in `insta_bot/src/insta_bot.py`).

## Gotchas for agents

- **Import path**: `main.py` only works when run from inside
  `insta_bot/` (see Running, above), because of the
  `from src.insta_bot import InstaBot` import.
- **Likely bug in `map_user_followers`**: it builds up
  `self.user_followers` but, when writing the cache file, dumps
  `self.followers` instead (an attribute set by the unrelated
  `map_followers` method). It writes to
  `insta_bot/cache/target-followers.json`. This is a known issue and is
  out of scope for documentation-only changes.
- **Cache path/name mismatch with `.gitignore`**: the root `.gitignore`
  lists `followers.json`, `following.json`, and `target-followes.json`
  (note the typo) at repo root, but the code actually writes
  `followers.json`, `following.json`, and `target-followers.json` inside
  `insta_bot/cache/`. The ignore rules currently do not match the real
  output paths/names. This is a known issue and out of scope here.
- **Minimal error handling**: several network calls (e.g.
  `get_userid`, `map_followers`, `map_following`) don't guard against
  unexpected responses beyond basic status-code/string checks
  (`req.content.decode('utf-8')[:3] == 'Ple'`), so failures can raise
  uncaught exceptions or silently misbehave.

## Contribution / PR notes

- Keep changes minimal and focused on the task at hand.
- Do not add heavy dependencies; the project intentionally has a single
  runtime dependency (`requests`).
