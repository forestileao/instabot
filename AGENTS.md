# AGENTS.md

## Overview

Insta Bot is a small hobby-scale Instagram automation tool written in Python 3.
It logs into an Instagram account, maps the followers/following of that
account (or of a "target" account), and runs two background loops that
follow suggested/target-follower accounts and unfollow accounts that don't
follow back. There is no web UI, database, or API server — it's a single
long-running script.

## Tech Stack

- Language: Python 3 (no version pin beyond "Python3" in `README.md`).
- Dependencies: only `requests~=2.24.0`, declared in `setup.py`. No
  `requirements.txt` or `pyproject.toml` exists — `setup.py` is the sole
  source of dependency metadata.
- Packaging: plain `setuptools` (`setup.py`), installed in editable mode.
- No web framework, no async library, no database, no ORM.
- Concurrency: two `threading.Thread`s with blocking `time.sleep()` calls
  for basic rate limiting (no asyncio, no task queue).

## Repository Layout

```
setup.py                     # package metadata + the single dependency (requests)
README.md                    # install/usage instructions
insta_bot/__init__.py        # empty package marker
insta_bot/main.py            # CLI entry point; loads credentials.json, runs InstaBot
insta_bot/credentials.json   # local credentials input (placeholder values only)
insta_bot/cache/             # output dir for generated follower/following JSON (.gitkeep only)
insta_bot/src/__init__.py    # empty package marker
insta_bot/src/insta_bot.py   # all bot logic: login, mapping, follow/unfollow, suggestions
```

## Setup & Running

```sh
pip3 install -e .          # from repo root, installs the requests dependency
```

Edit `insta_bot/credentials.json` with real values before running:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "john.doe"
}
```

Then run the entry point **from inside `insta_bot/`**, not from the repo
root:

```sh
cd insta_bot
python3 main.py
```

See "Known Gotchas" below for why the `cd insta_bot` step is required even
though `README.md`'s usage snippet omits it.

## Testing & Linting

There is currently **no test suite and no linter/formatter configuration**
in this repo — no `pytest`, `tox.ini`, `.flake8`, `pyproject.toml`,
pre-commit config, or CI workflow directory exists. Do not assume any of
these tools are wired up, and do not invent commands for them.

- If asked to add tests, prefer `pytest` under a new `tests/` directory and
  document the run command here once added.
- If asked to add linting/formatting, prefer `flake8`/`black` with a
  standard config, but note it won't be enforced by any existing CI.

## Coding Conventions Observed

- Plain classes/functions, no type hints, f-strings for building URLs.
- Manual `json`/`requests` calls; the only abstraction is
  `self.session = requests.Session()` inside `InstaBot.login`.
- `print()`-based logging — no `logging` module usage.
- Keep new code consistent with this untyped, dependency-light style
  unless a task explicitly asks to modernize it.

## Known Gotchas / Risks

- **Deprecated/private Instagram endpoints**: the bot relies on
  Instagram's legacy `?__a=1` profile JSON endpoint and
  `graphql/query/?query_hash=...` endpoints with hardcoded query hashes.
  These are undocumented, unsupported, and can break or be blocked by
  Instagram without notice; using them may also violate Instagram's Terms
  of Service and risks the automated account being flagged/banned. Treat
  any change touching login/mapping/follow logic as inherently fragile.
- **Import path quirk in `main.py`**: `insta_bot/main.py` does
  `from src.insta_bot import InstaBot` and opens `./credentials.json` using
  a relative path. Both only resolve correctly when the script is run with
  the current working directory set to `insta_bot/` (i.e.
  `cd insta_bot && python3 main.py`). Running `python3 main.py` from the
  repo root, as `README.md`'s snippet suggests, will fail. Fixing this is
  out of scope unless a task explicitly asks for it — call it out clearly
  in the change description if you do fix it, since it changes documented
  usage.
- **`setup.py` packages list**: `setup.py` only lists `packages=['insta_bot']`;
  it does not declare `insta_bot.src` as a package. Editable/installed
  behavior for the `src` subpackage outside this repo directory is
  unreliable. Same caveat as above if you decide to fix it.
- **Credentials file is tracked in git**: `insta_bot/credentials.json` is
  committed with placeholder values (`your_username`, `your_password`,
  empty `target_username`). Never commit real Instagram credentials to
  this file or anywhere else in the repo.
- **`.gitignore` mismatch**: `.gitignore` ignores `followers.json`,
  `following.json`, and `target-followes.json` (note the typo) at the repo
  root, but the code actually writes `followers.json`, `following.json`,
  and `target-followers.json` under `insta_bot/cache/`. The ignore rules do
  not match the real output location. Regardless of the exact ignore
  pattern, treat any generated cache JSON under `insta_bot/cache/` as data
  that should never be committed.
- **No graceful shutdown**: the `just_follow`/`just_unfollow` background
  threads rely on blocking `sleep()` calls for rate limiting and have no
  signal handling or clean shutdown path.

## Guidance for Agents Making Changes

- Don't add new dependencies unless truly necessary; keep the footprint
  minimal (currently only `requests`).
- Don't commit real Instagram credentials or generated
  `followers.json` / `following.json` / `target-followers.json` cache data.
- If you fix the `main.py` import issue or the `setup.py` packages list,
  say so explicitly in the change description, since it alters documented
  usage.
- Since there is no automated test suite, describe and manually verify any
  behavioral change in the PR description. If you add automated tests, set
  up `pytest` from scratch and document the run command in this file.
