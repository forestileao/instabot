# agents.md

Guidance for AI coding agents working in this repository.

## Project overview

Insta Bot is a small, single-package Python script that automates an
Instagram account: it maps a target user's followers, follows them, and
unfollows accounts that don't follow back. There is no web server, no
database, and no build system beyond a plain `setuptools` package.

Layout:
- `insta_bot/main.py` — entry point, reads `insta_bot/credentials.json`
  and calls `InstaBot(...).start(...)`.
- `insta_bot/src/insta_bot.py` — all logic lives in the `InstaBot` class.
- `insta_bot/cache/` — runtime output (`followers.json`,
  `following.json`, `target-followers.json`); only `.gitkeep` is tracked.
- `setup.py` — package metadata (`insta-bot`), single dependency.

## Tech stack

- Python 3, no minimum version pinned.
- `requests~=2.24.0` — the only third-party dependency.
- Standard library only otherwise: `json`, `time`/`sleep`, `threading`,
  `os.path`.
- No async code, no type hints. Match the existing plain, untyped style
  when adding code.

## Setup commands

Run from the repository root:

```sh
pip3 install -e .
```

Configure credentials before running the bot by editing
`insta_bot/credentials.json`:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "john.doe"
}
```

Never commit real credentials. This file is tracked as a placeholder —
keep it that way in commits/PRs; only fill in real values locally.

## Run commands

The bot must be run from inside the `insta_bot/` directory, because
`main.py` uses the relative import `from src.insta_bot import InstaBot`:

```sh
cd insta_bot
python3 main.py
```

Running it as `python3 -m insta_bot.main` from the repo root will fail
with an import error. This is a known quirk of the current code — don't
"fix" it as a side effect of an unrelated task; only change the import
style if that is the explicit goal of the work.

Output cache files (`followers.json`, `following.json`,
`target-followers.json`) are written to `insta_bot/cache/` at runtime.
Do not commit generated cache files.

## Test / lint commands

There are currently no tests, no CI, and no linter/formatter configured
in this repo. Don't assume `pytest`, `flake8`, `black`, etc. are set up.

If a task asks you to add tests, a reasonable approach is:
- Add a `tests/` directory and use `pytest`.
- Add a `requirements-dev.txt` (or `extras_require` in `setup.py`) for
  test-only dependencies.
- Update `setup.py` only as needed to support running the tests.

Do not invent CI workflows or linting config unless a task explicitly
asks for it.

## Code style conventions

Follow the conventions already used in `insta_bot/src/insta_bot.py`:
- 4-space indentation.
- f-strings for string formatting.
- snake_case for methods and variables; `InstaBot` is the only class.
- Plain `print()` statements for logging/status output — no `logging`
  module is used.
- Keep related behavior grouped as methods on `InstaBot` rather than
  introducing new modules/classes for small additions; put substantial
  new logic under `insta_bot/src/`.

## Safety and behavioral notes

`InstaBot` logs in and scrapes Instagram's private, undocumented
GraphQL endpoints using hardcoded `query_hash` values. This is not a
stable, documented API:

- It can break at any time if Instagram changes its internal endpoints
  or `query_hash` values — treat failures here as expected, not
  necessarily bugs to silently "fix" with guesses.
- Automating follows/unfollows like this violates Instagram's Terms of
  Service and can get real accounts rate-limited or banned.
- This code must never be modified to increase request rates, remove
  backoff, or otherwise make it more aggressive. Preserve existing
  rate-limit handling such as the `sleep(10 * 60)` waits after a failed
  follow/unfollow request, and the `sleep(3 * 60)` backoff on errors.
- Do not add features intended for spamming, mass-following unrelated
  accounts, or evading Instagram's abuse detection.

## PR / commit guidance

- Keep changes minimal and focused on the requested task.
- Never commit real Instagram credentials or generated files from
  `insta_bot/cache/`.
- Don't introduce CI, test suites, or linting configuration unless a
  task explicitly asks for it.
