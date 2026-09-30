# AGENTS.md

## Overview
Insta Bot is a small Python script that automates Instagram follow/unfollow
activity through Instagram's private web endpoints (the same `graphql` and
`web/friendships` calls the website itself uses, not the official API). It
logs in with a username and password, then starts two background threads.
The follow thread maps a source list and follows from it: a target user's
followers when `target_username` is set, otherwise Instagram's "suggested
users" list (it still maps the logged-in user's followers first, but does
not follow that list). The unfollow thread unfollows accounts you follow
that don't follow you back. `main.py` leaves the `start()` defaults in
place, and those defaults do not stop either thread; see "Known rough
edges".

## Layout
- `insta_bot/` - the Python package.
  - `main.py` - entry point. Loads `credentials.json`, builds an `InstaBot`
    instance, and calls `bot.start(...)`.
  - `credentials.json` - holds `username`, `password`, and
    `target_username`. Read at runtime; not meant to contain real secrets in
    version control.
  - `src/insta_bot.py` - all bot logic lives in the `InstaBot` class here.
  - `src/__init__.py`, `insta_bot/__init__.py` - empty package markers.
  - `cache/` - output folder for the JSON files the bot writes while
    mapping followers/following (contains only `.gitkeep` in the repo).
- `setup.py` - packaging metadata (`insta-bot`, version `1.0.0`), declares
  the single runtime dependency `requests~=2.24.0`. It installs the
  `insta_bot` package only, not `insta_bot.src`.
- `README.md` - short install/usage instructions for end users.
- `.gitignore` - ignores `*.egg`, `*.egg-info`, `__pycache__`, `venv`, and
  the generated `followers.json`, `following.json`, `target-followes.json`
  (note the existing typo, kept as-is).

## Setup and run
1. Requires Python 3.
2. From the repository root, install the package in editable mode; this
   pulls in `requests` per `setup.py`:
   ```sh
   pip3 install -e .
   ```
3. Edit `insta_bot/credentials.json` and fill in `username`, `password`,
   and (optionally) `target_username`. Leaving `target_username` empty
   makes the bot follow from Instagram's suggested-users feed instead of a
   specific account's followers.
4. Run the entry point from inside the `insta_bot/` package folder (the
   import `from src.insta_bot import InstaBot` in `main.py` is relative to
   that directory, and `./credentials.json` is opened relative to the
   current working directory):
   ```sh
   cd insta_bot
   python3 main.py
   ```

## Checking changes
The repo has no automated tests, linters, or CI. Use these offline checks,
which need no credentials or network access:
```sh
python3 -m py_compile insta_bot/main.py insta_bot/src/insta_bot.py
cd insta_bot && python3 -c "from src.insta_bot import InstaBot"
```
Run both from the repository root. The import check needs `requests`
installed (see "Setup and run").

Running `main.py` hits live Instagram endpoints with real credentials and
follows/unfollows real accounts. Do not run it, and do not commit real
values to `insta_bot/credentials.json`.

## Key behaviors (in `src/insta_bot.py`)
- `login()` - opens a `requests.Session`, grabs a CSRF token from
  instagram.com, encrypts the password with `generate_encrypted_password()`
  (a `#PWD_INSTAGRAM_BROWSER:...` string, not real encryption), and posts to
  `/accounts/login/ajax/`. On success it prints the logged-in user
  id/username and stores `self.user_id`. On a failed authentication it
  prints `> Erron on login authentication` (typo in source) and returns the
  parsed body without setting `self.user_id`. A `ConnectionError` prints
  `> Connection refused`. `start()` still launches both threads if login
  fails.
- `get_userid(username)` - resolves a username to its numeric id via
  `https://instagram.com/{username}/?__a=1`. Returns `None` when the status
  is not 200.
- `map_followers()` / `map_user_followers(username, limit=1000)` - page
  through the `edge_followed_by` GraphQL query (hard-coded `query_hash`
  `c76146de99bb02f6415203be841dd25a`) to build `self.followers` /
  `self.user_followers`. A JSON dump is written only when the collected
  count exactly equals the stop count. `map_followers()` writes
  `cache/followers.json` from `self.followers` when `count == self.foll_num`.
  `map_user_followers()` writes `cache/target-followers.json` when
  `count == limit`, but dumps `self.followers`, not `self.user_followers`
  (see "Known rough edges"). An early `status == fail` break skips the
  write. Both methods read `self.verbose`.
- `map_following()` - same paging pattern using the `edge_follow` query
  hash `d04b0a864b4b54837c0d870b0e77e076` to build `self.following`, and
  writes `cache/following.json` only when `count == self.following_num`.
- `get_suggested_followers()` - calls the suggested-users GraphQL query
  (`query_hash` `ed2e3ff5ae8b96717476b62ef06ed8cc`), skips nodes whose
  `description` starts with `Ins`, and returns a list of `{username, id}`
  candidates. Returns `None` when the status is not 200.
- `follow_user(userid)` / `unfollow_user(userid)` - POST to
  `/web/friendships/{id}/follow/` or `/unfollow/`. Print a `[status_code]`
  marker (no newline) and return `False` when the status is not 200 or the
  body starts with `Ple`; otherwise `True`.
- `just_follow()` - loop used by the follow thread. If `other_user` is
  false, it calls `map_followers()`, then follows accounts from
  `get_suggested_followers()` while `self.foll_num < self.hoped_foll`. If
  `other_user` is true, it calls `map_user_followers(self.target_username)`,
  then repeatedly walks that same `self.user_followers` list. Both `while`
  conditions are `hoped_foll` OR `other_user`, so a target makes this
  thread run forever. Neither count is updated when a follow succeeds. A
  failed follow sleeps 10 minutes. A bare `except` prints
  `> Error in suggested` and sleeps 3 minutes.
- `just_unfollow()` - loop used by the unfollow thread: maps followers and
  following, then unfollows anyone in `self.following` whose
  `{username, id}` dict is not in `self.followers`, and re-maps between
  passes. The `while` condition is `following_num > foll_num` OR
  `unfollow_all_not_followers`. A `count >= 50` break sits inside the
  per-user loop, but `count` is set to `1` on every iteration and is only
  incremented for users who already follow back, so the cap never fires
  (see "Known rough edges"). A failed unfollow sleeps 10 minutes and
  retries that same user.
- `start(target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False)`
  - sets instance flags (`other_user` is `True` only when
    `target_username` is non-empty), stores `hoped_foll`, calls `login()`,
    then starts `just_follow` and `just_unfollow` each on its own
    non-daemon `Thread` and returns without joining them. `main.py` passes
    only `target_username` and `verbose=False`, so `hoped_foll` stays 2000
    and `unfollow_all_not_followers` stays `True`.

## Data files
- Mapped lists are written as JSON under `insta_bot/cache/`
  (`path.dirname(__file__) + '/../cache/...'` from `src/insta_bot.py`):
  `followers.json`, `following.json`, and `target-followers.json`.
- Those writes happen only when the page loop hits its exact stop count.
  `target-followers.json` is dumped from `self.followers`, not from the
  `self.user_followers` list `map_user_followers()` just built.
- The `.gitignore` lists similarly named files (`followers.json`,
  `following.json`, `target-followes.json`, note the typo). Because of the
  typo, the generated `target-followers.json` is not actually ignored.

## Conventions
- Standard library plus `requests` only; no other third-party
  dependencies are used or should be added without updating `setup.py`.
- All bot behavior lives on the `InstaBot` class using `snake_case` method
  names (`map_followers`, `follow_user`, `just_unfollow`, etc.).
- Console progress is printed with a leading `>` or `***`/`[*]` marker
  (e.g. `> Followed {username}`, `*** Mapping followers ***`,
  `[*] Followers:`). Follow/unfollow status codes are printed as
  `[status_code]` with no trailing newline.
- Credentials are always read from `credentials.json` at runtime; never
  hard-code usernames, passwords, or tokens in source.

## Known rough edges (do not "fix" silently, but be aware of them)
- GraphQL `query_hash` values are hard-coded strings tied to Instagram's
  current frontend build; they can go stale if Instagram changes them.
- Several loops use bare/broad `except:` blocks (e.g. in `just_follow`)
  that swallow all errors and just sleep and retry.
- `credentials.json` ships with placeholder values and is not excluded by
  `.gitignore`, so real credentials should not be committed here.
- `map_user_followers()` writes `self.followers` to
  `cache/target-followers.json` instead of `self.user_followers`. The cache
  file does not contain the target account's followers.
- `just_follow()` uses `or self.other_user` in both `while` conditions, so
  a non-empty target never stops the follow thread. Without a target,
  `self.foll_num` is only the snapshot from `map_followers()` and is not
  increased when follows succeed, so the `hoped_foll` check does not track
  progress either.
- The 50-per-pass cap in `just_unfollow()` is dead code: `count = 1` runs
  inside the `for` loop, so `if count >= 50` never breaks. `count` is also
  incremented only when the user is already a follower, not when an
  unfollow happens. The `while` stays true for as long as
  `unfollow_all_not_followers` is true, which is the default `start()`
  uses and the value `main.py` leaves in place.
- `map_followers()`, `map_user_followers()`, and `map_following()` read
  `self.verbose`. Only `start()` sets that attribute. Calling a map method
  before `start()` raises `AttributeError`.
- `map_following()` mixes tabs into the indent of the closing `})` of the
  `self.following.append({...})` block. `py_compile` currently accepts the
  file; do not reindent that line as a drive-by cleanup.
- `login()` does not stop `start()` when authentication fails. Both threads
  still start, and later use of `self.user_id` or `self.session` fails.
