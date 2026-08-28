# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project overview

`insta-bot` (v1.0.0) is a small Python 3 script that automates following and
unfollowing Instagram accounts. It logs into Instagram's private,
undocumented web endpoints (`/accounts/login/ajax/`, `/graphql/query/`,
`/web/friendships/{id}/follow|unfollow/`) directly with the `requests`
library — there is no official API client and no OAuth. Requests to the
GraphQL endpoint use hardcoded `query_hash` values that Instagram controls
and can change or invalidate at any time without notice.

At a high level, `InstaBot.start()`:
1. Logs in with a username/password from `credentials.json`.
2. Maps (paginates and caches) your followers, your following, and
   optionally a target user's followers.
3. Spawns two background threads: one that follows suggested/target users
   until a follower goal is reached, and one that unfollows accounts that
   don't follow you back.

## Tech stack

- Python 3 (developed/runs on 3.11; no version pin enforced elsewhere).
- Single third-party dependency: `requests~=2.24.0` (see `setup.py`).
- Everything else is standard library: `json`, `time`, `threading`,
  `os.path`.
- No web framework, no database, no test suite, no linter/formatter
  config, and no CI pipeline configured in this repo.

## Repository layout

```
.
├── README.md                    # install + usage instructions
├── setup.py                     # packaging metadata (name: insta-bot)
├── AGENTS.md                    # this file
├── .gitignore                   # ignores egg-info, __pycache__, venv,
│                                 #   followers.json, following.json,
│                                 #   target-followes.json (sic)
└── insta_bot/
    ├── __init__.py              # empty
    ├── main.py                  # entry point: reads ./credentials.json,
    │                             #   builds InstaBot, calls bot.start()
    ├── credentials.json         # username/password/target_username
    │                             #   template, committed with placeholders
    ├── cache/
    │   └── .gitkeep             # target dir for followers.json,
    │                             #   following.json, target-followers.json
    └── src/
        ├── __init__.py          # empty
        └── insta_bot.py         # the InstaBot class (all bot logic)
```

`insta_bot/__init__.py` and `insta_bot/src/__init__.py` are both empty, so
despite `setup.py` declaring `packages=['insta_bot']`, the code is written
and imported as loose scripts (`from src.insta_bot import InstaBot`) rather
than as a proper installable package with relative imports.

## Setup and run

```sh
git clone https://github.com/forestileao/instabot.git
cd instabot
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip3 install -e .                                  # installs requests~=2.24.0
```

Edit `insta_bot/credentials.json` with real values:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "john.doe"
}
```

Then run it **from inside `insta_bot/`**:

```sh
cd insta_bot
python3 main.py
```

### Working-directory gotcha

`main.py` does `from src.insta_bot import InstaBot` (a plain, non-package
relative import) and opens `./credentials.json` as a relative path. Both of
these only resolve correctly when the current working directory is
`insta_bot/`. Running `python3 insta_bot/main.py` from the repo root will
fail with `ModuleNotFoundError` and/or `FileNotFoundError`.

## Conventions

- 4-space indentation, no semicolons, standard PEP 8-ish style but not
  enforced by tooling.
- Classes are `PascalCase` (`InstaBot`); methods, functions, and variables
  are `snake_case`.
- URLs are built with f-strings and string concatenation directly against
  `self.base_url = 'https://www.instagram.com'`.
- User-facing progress is printed to stdout, not logged: lines that report
  state transitions use a `> ` prefix (e.g. `> Logged in ...`), lines that
  announce the start of a phase use a `*** ... ***` banner (e.g.
  `*** Mapping followers ***`).
- The `verbose` flag (passed into `InstaBot.start()`) gates extra
  per-user prints inside the mapping loops; it does not use the `logging`
  module.
- Cached results are written as JSON under `insta_bot/cache/`, addressed
  relative to the source file via `os.path.dirname(__file__) + '/../cache/...'`
  rather than the process's current working directory.

## Known gotchas / existing issues

Document these; do not silently "fix" them as a side effect of unrelated
changes — if asked to address one, call it out explicitly in the change.

- **Import/CWD coupling**: see "Working-directory gotcha" above. Anyone
  scripting or testing this code needs to `cd insta_bot` first, or the
  import/paths must be reworked into a real package.
- **`map_user_followers` writes the wrong variable**: at the end of
  `map_user_followers`, it dumps `self.followers` into
  `.../cache/target-followers.json`, but the method builds up
  `self.user_followers`. This looks like a bug — the target user's
  followers cache is likely never populated correctly (and only works at
  all if `map_followers()` happened to run first and set `self.followers`).
- **`.gitignore` has a filename typo**: it ignores `target-followes.json`
  (missing an `r`), while the code writes `target-followers.json`. The
  generated cache file is therefore not actually gitignored.
- **Bare `except:` in `just_follow`**: swallows all exceptions (including
  `KeyboardInterrupt`/`SystemExit`) and just sleeps 3 minutes before
  retrying; makes failures hard to diagnose.
- **`login()` can leave `self.session` unset**: on
  `requests.exceptions.ConnectionError` it prints a message and returns
  `None` without setting `self.session`, so subsequent calls (`get_userid`,
  `map_followers`, etc.) will raise `AttributeError` instead of failing
  gracefully.
- **No retry/backoff strategy beyond fixed sleeps** (`sleep(10 * 60)`,
  `sleep(3 * 60)`), and no rate-limit detection beyond checking for a
  `'Ple...'` (likely "Please wait...") prefix in the response body.
- **Fragile dependency on private Instagram internals**: the `query_hash`
  values in `map_followers`, `map_user_followers`, `map_following`, and
  `get_suggested_followers` are opaque IDs tied to Instagram's current
  GraphQL schema. Instagram can change or retire these at any time,
  breaking the bot with no compile-time warning. There is no abstraction
  layer isolating these constants — they are inlined into URL strings.
- **`enc_password` is a plaintext-style scheme** (`'#PWD_INSTAGRAM_BROWSER:0:<timestamp>:<password>'`)
  sent over HTTPS; it is not real client-side encryption, just Instagram's
  expected wire format for password submission.
- **`credentials.json` holds plaintext secrets and is committed** to the
  repo (currently with placeholder values). Never commit real credentials
  to this file or anywhere else in the repo.

## Agent do / don't

- Do keep the single-dependency footprint (`requests` only) unless a task
  explicitly calls for adding something.
- Do preserve the existing `print()`-based progress style (`>` / `***`
  prefixes, `verbose` gating) unless asked to introduce structured logging.
- Do **not** commit real Instagram credentials, cookies, or session data.
  `insta_bot/credentials.json` must stay a placeholder template.
- Do **not** attempt to actually log in to Instagram or exercise the
  network code paths against the live site when verifying changes —
  Instagram's automation detection can lock out real accounts. Prefer
  reasoning about the code, mocking `requests.Session`, or unit-testing
  pure helper logic (e.g. `generate_encrypted_password`).
- If adding tooling (tests, linting, type checking, CI), note in the PR
  description that none of this existed before, since there is currently
  no test suite, linter config, or CI pipeline to align with.
- Fixing the "Known gotchas" above is out of scope unless a task
  specifically asks for it — when it does, call out which gotcha is being
  addressed.
