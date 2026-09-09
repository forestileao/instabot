# AGENTS.md

Guidance for AI coding agents working in this repository.

## 1. Project overview

Insta Bot is a small Python 3 command-line Instagram automation tool. It logs
into an Instagram account, maps its followers/following (or the followers of
a chosen "target" account), and then runs two background loops that follow
new users (either suggested users or the target account's followers) and
unfollow accounts that don't follow back. It works by talking directly to
Instagram's private/AJAX and GraphQL endpoints using `requests` — there is no
official API client and no web framework involved.

## 2. Tech stack

- Language: Python 3 (README only requires "Python3"; no pinned minor version).
- Runtime dependency: `requests~=2.24.0` (see `setup.py`).
- Standard library used: `json`, `time` / `time.sleep`, `os.path`, `threading.Thread`.
- No test framework, no linter/formatter config, no type checking, no CI is configured in this repo.

## 3. Repository layout

```
.
├── setup.py                  # packaging: name "insta-bot", installs `requests`
├── README.md                 # user-facing setup/run instructions
└── insta_bot/                 # the only Python package
    ├── __init__.py            # empty, namespace file
    ├── main.py                 # entry point: loads credentials.json, runs the bot
    ├── credentials.json        # username/password/target_username (placeholders)
    ├── cache/                  # generated JSON files land here (gitkeeped, empty)
    │   └── .gitkeep
    └── src/
        ├── __init__.py         # empty, namespace file
        └── insta_bot.py        # the InstaBot class — all bot logic lives here
```

## 4. Setup

```sh
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

`pip install -e .` installs the package in editable mode and pulls in the
single dependency, `requests`.

## 5. Configuration

Edit `insta_bot/credentials.json`:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": ""
}
```

- `username` / `password`: the Instagram account the bot logs in as.
- `target_username`: optional. Leave empty (`""`) to have the bot follow
  Instagram's *suggested users* for your own account. Set it to another
  account's username to have the bot follow that account's followers instead.

Never commit real credentials. The version of `credentials.json` committed to
this repo contains placeholder values only — keep it that way, and remind
users/agents not to replace it with real secrets in a commit.

## 6. Running

The bot must be run from inside the `insta_bot/` package directory, because
`main.py` opens `./credentials.json` as a relative path and imports
`src.insta_bot` as a relative package:

```sh
cd insta_bot
python3 main.py
```

Runtime behavior (`InstaBot.start`):

1. Logs in via `login()`, obtaining a session and CSRF token.
2. Spawns two daemon-less threads that run continuously:
   - `just_follow`: maps followers (own or target's) once, then repeatedly
     follows users (suggested users, or the target's followers) until the
     follower goal (`hoped_foll`, default 2000) is reached or the loop
     condition otherwise ends.
   - `just_unfollow`: maps followers and following, then unfollows anyone in
     "following" who is not in "followers", re-mapping after each pass.
3. Both loops sleep between requests and back off (10 minutes) after a
   failed follow/unfollow call, to avoid hammering Instagram.

There is no CLI flag support today — all behavior is controlled via
`credentials.json` plus the keyword arguments passed to `start()` in
`main.py` (`target_username`, `hoped_foll`, `unfollow_all_not_followers`,
`verbose`).

## 7. Conventions for agents

- Keep the flat single-class design. Add new behavior as methods on
  `InstaBot` in `insta_bot/src/insta_bot.py` rather than introducing new
  modules/classes unless there's a strong reason to split things up.
- Match existing style: 4-space indentation, `snake_case` names, f-strings
  for string building, and `print`-based logging prefixed with `>` (per-item
  events) or `***` (section/phase headers).
- Preserve the cache file convention: outputs are written relative to the
  module using `path.dirname(__file__) + '/../cache/<name>.json'`
  (`followers.json`, `following.json`, `target-followers.json`). Don't hardcode
  absolute or CWD-relative paths.
- There is no test suite. If you add tests, note that none is currently wired
  up (no pytest/unittest config, no CI). Mock all network calls — never make
  tests hit real Instagram endpoints.

## 8. Gotchas / known issues

Be aware of these so you don't "fix" things that weren't asked for, or get
surprised by existing behavior:

- `map_user_followers` builds up `self.user_followers` as it maps a target's
  followers, but the cache-write branch at the `limit` cutoff dumps
  `self.followers` (not `self.user_followers`) into `target-followers.json`.
  This looks like a bug. Don't silently "fix" it unless the task explicitly
  asks you to — flag it instead.
- `.gitignore` lists `target-followes.json` (typo, missing an "r"), while the
  code writes `target-followers.json`. As a result the generated
  `target-followers.json` is **not** actually ignored by git. Same caveat as
  above: don't silently correct the typo unless asked.
- Instagram's private endpoints, `query_hash` values (used for followers /
  following GraphQL queries and suggested users), and the `enc_password`
  format used at login change frequently and without notice. If login or
  mapping breaks, treat it as an expected consequence of Instagram changing
  their private API, not necessarily a regression in this code.
- Control flow uses broad bare `except:` blocks and `while True` /
  open-ended loops in `just_follow` and `just_unfollow`. Be careful when
  refactoring these — they're easy to accidentally turn into infinite loops
  with no exit path, or to swallow errors that should surface.
- Rate-limit backoff: on a failed follow/unfollow call, the code sleeps 10
  minutes before retrying (`sleep(10 * 60)`), and on an exception in
  `just_follow` it sleeps 3 minutes. Preserve these (or similarly generous)
  backoffs — removing/shortening them risks getting the account rate-limited
  or banned.

## 9. Safety / legal note

Automating actions on Instagram (mass following/unfollowing, scraping
private GraphQL endpoints) may violate Instagram's Terms of Service and can
result in the account being rate-limited or banned. Agents working on this
project should:

- Not add features that increase the scale or aggressiveness of automated
  behavior (e.g., removing sleep/backoff logic, raising follow limits
  drastically, parallelizing requests).
- Keep real credentials out of version control at all times — only
  placeholder values belong in `credentials.json` in this repo.
