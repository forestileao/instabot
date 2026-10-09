# AGENTS.md

## Overview
Insta Bot is a small Python script that automates Instagram follow/unfollow
activity through Instagram's private web endpoints (the same `graphql` and
`web/friendships` calls the website itself uses, not the official API). It
logs in with a username and password, starts two background threads, and
returns.
- Follow thread: follows a target account's followers when
  `target_username` is non-empty; otherwise follows Instagram's suggested
  users (it still maps the logged-in account's followers, but does not
  follow that list).
- Unfollow thread: unfollows accounts you follow that do not follow you back.

`main.py` only passes `target_username` and `verbose=False`, so `hoped_foll`
stays `2000` and `unfollow_all_not_followers` stays `True`. Those defaults do
not stop either thread (see "Known rough edges").

## Layout
- `insta_bot/` - the Python package.
  - `main.py` - entry point. `load_credentials()` reads `CREDENTIALS_PATH`
    (`./credentials.json`), then it builds an `InstaBot` and calls
    `bot.start(target_username=..., verbose=False)`.
  - `credentials.json` - `username`, `password`, `target_username`. The
    committed file has placeholders and an empty `target_username`.
  - `src/insta_bot.py` - all bot logic: the `InstaBot` class, module
    constants, and private helpers. Reuse the constants and helpers; do not
    re-inline them.
  - `src/__init__.py`, `insta_bot/__init__.py` - empty package markers.
  - `cache/` - output folder for the bot's JSON files (only `.gitkeep` in
    the repo). See "Data files".
- `tests/test_insta_bot.py` - automated tests (16 tests). Inserts the
  `insta_bot/` directory on `sys.path`, then imports `src.insta_bot` and
  `main`.
- `setup.py` - packaging metadata (`insta-bot`, version `1.0.0`), one runtime
  dependency `requests~=2.24.0`. `packages` lists only `insta_bot`, not
  `insta_bot.src`, so the `src` import path is not installed.
- `README.md` - short install/usage instructions for end users.
- `.gitignore` - ignores `*.egg`, `*.egg-info`, `__pycache__`, `venv`, and
  some generated cache files (see "Data files").

## Setup and run
1. Requires Python 3.
2. From the repository root, install in editable mode (pulls in `requests`):
   ```sh
   pip3 install -e .
   ```
3. Edit `insta_bot/credentials.json`: `username`, `password`, and optionally
   `target_username`. Empty selects the suggested-users follow path; a
   non-empty value selects that account's followers.
4. Run from inside `insta_bot/`. Both `from src.insta_bot import InstaBot`
   and the open of `./credentials.json` are relative to that directory:
   ```sh
   cd insta_bot
   python3 main.py
   ```
   Running it acts on a real account; see "Conventions" before doing so.

## Checking changes
There are no linters and no CI. These offline checks need no credentials or
network, only `requests` installed. Run them from the repository root:
```sh
python3 -m py_compile insta_bot/main.py insta_bot/src/insta_bot.py
cd insta_bot && python3 -c "from src.insta_bot import InstaBot"
python3 tests/test_insta_bot.py
```
`tests/test_insta_bot.py` currently runs 16 tests. It inserts the package
directory on `sys.path` itself, so do not prescribe `python3 -m unittest`.

## Key behaviors (in `src/insta_bot.py`)
Module constants (copy these; do not inline the values):
- `BASE_URL` is `https://www.instagram.com`. It is stored as
  `self.base_url`.
- `USER_AGENT` is a hard-coded Chrome 51 on Chrome OS string
  (`Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like
  Gecko) Chrome/51.0.2704.64 Safari/537.36`).
- `FOLLOWERS_QUERY_HASH` is `c76146de99bb02f6415203be841dd25a`.
- `FOLLOWING_QUERY_HASH` is `d04b0a864b4b54837c0d870b0e77e076`.
- `SUGGESTED_QUERY_HASH` is `ed2e3ff5ae8b96717476b62ef06ed8cc`.
- `FOLLOWERS_PAGE_SIZE` is 24, `FOLLOWERS_NEXT_PAGE_SIZE` is 12,
  `FOLLOWING_PAGE_SIZE` is 24.
- `RATE_LIMIT_PREFIX` is `Ple`. `RATE_LIMIT_WAIT_SECONDS` is `10 * 60` (600).
  `SUGGESTED_ERROR_WAIT_SECONDS` is `3 * 60` (180).
  `INSTAGRAM_DESCRIPTION_PREFIX` is `Ins`.
- `SUGGESTED_QUERY` is the suggested-users variables dict.

Private helpers (call these; do not re-inline them):
- `_set_csrf` sets `x-csrftoken` from the response cookie.
- `_get_json` loads a GET body as JSON.
- `_connection_url` builds a compact variables string with no spaces. Do not
  switch it to `json.dumps`.
- `_user_record` returns `{username, id}`.
- `_write_cache` writes `path.dirname(__file__) + '/../cache/' + filename`.
- `_friendship_action` owns the follow/unfollow POSTs to
  `/web/friendships/{id}/follow/` or `/unfollow/`. It prints `[status_code]`
  with no newline and returns `False` when the status is not 200 or the body
  starts with `Ple`; otherwise `True`.
- `_suggested_users` skips nodes whose `description` starts with `Ins` and
  returns `{username, id}` dicts.
- `_follow_batch` prints `*** Following Users ***` and owns the bare
  `except`: it prints `> Error in suggested` and sleeps
  `SUGGESTED_ERROR_WAIT_SECONDS`, including when the suggested call returns
  `None`.
- `_follow_one` prints `> Followed {username}` on success; otherwise it
  prints `> Waiting 10 min until next FOLLOW request`, sleeps
  `RATE_LIMIT_WAIT_SECONDS`, and moves on.
- `_unfollow_non_followers` unfollows each followed account whose
  `{username, id}` dict is not in `self.followers`.
- `_unfollow_until_success` retries the same user: on failure it prints
  `> Waiting 10 minutes until next UNFOLLOW request.` and sleeps
  `RATE_LIMIT_WAIT_SECONDS`; on success it prints `> Unfollowed {username}`.

Public methods:
- `login()` - opens a `requests.Session` with `USER_AGENT` and a `Referer`
  of `BASE_URL`, GETs `BASE_URL` for a `csrftoken` cookie, then posts
  `username` plus `generate_encrypted_password()` to
  `/accounts/login/ajax/`. `_set_csrf` runs after the home GET and after the
  login POST. The password string is
  `#PWD_INSTAGRAM_BROWSER:0:{unix_time}:{plaintext}`, not real encryption.
  On `authenticated` it stores `self.user_id` and prints
  `> Logged in (user:..., id:...)`. Otherwise it prints
  `> Erron on login authentication` (typo in source) and the parsed body,
  and does not set `self.user_id`. A `requests.exceptions.ConnectionError`
  prints `> Connection refused`. Returns the parsed body, or `None` on
  `ConnectionError`.
- `get_userid(username)` - GETs `https://instagram.com/{username}/?__a=1`
  (no `www`; it does not use `BASE_URL`). Returns the GraphQL user id on
  status 200, otherwise `None`.
- `map_followers()` - pages `edge_followed_by` with `FOLLOWERS_QUERY_HASH`
  (`FOLLOWERS_PAGE_SIZE`, then `FOLLOWERS_NEXT_PAGE_SIZE`) into
  `self.followers` and sets `self.foll_num` from the first page's `count`.
  Writes `followers.json`. Reads `self.verbose`.
- `map_user_followers(username, limit=1000)` - same query hash, for
  `get_userid(username)`, into `self.user_followers`. Sets
  `self.user_foll_num` from the first page. Stops when `count == limit` and
  writes `target-followers.json`. Reads `self.verbose`.
- `map_following()` - pages `edge_follow` with `FOLLOWING_QUERY_HASH`
  (`FOLLOWING_PAGE_SIZE` on every page) into `self.following` and sets
  `self.following_num`. Writes `following.json`. Reads `self.verbose`.
- `get_suggested_followers()` - GETs `SUGGESTED_QUERY_HASH` with
  `json.dumps(SUGGESTED_QUERY)` (suggested users keep `json.dumps`).
  Prints `> Getting Suggested` and the payload status, then returns
  `_suggested_users` output, or `None` if the status is not 200.
- `follow_user(userid)` / `unfollow_user(userid)` - call
  `_friendship_action` with `follow` / `unfollow`.
- `just_follow()` - follow-thread loop.
  - No target: `map_followers()`, then loops `_follow_batch` with
    `get_suggested_followers` while `self.foll_num < self.hoped_foll`.
  - Target set: `map_user_followers(target)` once, then loops `_follow_batch`
    with a lambda returning `self.user_followers` while
    `self.user_foll_num < self.hoped_foll or self.other_user`.
  - Loop exits: see "Known rough edges".
- `just_unfollow()` - unfollow-thread loop. Maps followers and following,
  then while `self.following_num > self.foll_num or
  self.unfollow_all_not_followers` prints `[*] Followers:` and
  `[*] Following:` counts, calls `_unfollow_non_followers`, and maps again.
  It has no `try`/`except`; an error kills the thread.
- `start(target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False)`
  - sets `self.unfollow_all_not_followers`, `self.verbose`, and
    `self.hoped_foll`. Sets `self.other_user` to `False`, and sets
    `self.target_username` and `self.other_user = True` only when
    `len(target_username) > 0`. Calls `login()`, starts `just_follow` and
    `just_unfollow` on non-daemon `Thread`s, and returns without joining.
    The two threads share one `requests.Session` with no lock.

## Data files
Cache files are written by `_write_cache` to `insta_bot/cache/` regardless of
the process cwd: `followers.json`, `following.json`, `target-followers.json`.
- A file is written only when the page loop's collected count exactly equals
  its stop value: `count == self.foll_num`, `count == limit`, or
  `count == self.following_num`. There is no `has_next_page` check. A short
  last page or a total the edges never hit skips the write and keeps paging
  until `status == fail` or an uncaught error. A `status == fail` response
  breaks without writing.
- `target-followers.json` is dumped from `self.followers`, not from the
  `self.user_followers` list just built, so it is not the target account's
  followers.
- `.gitignore` lists `followers.json`, `following.json`, and the misspelled
  `target-followes.json` (typo kept as-is). Those names match in any
  directory. `target-followers.json` is therefore not ignored.

## Conventions
- Standard library plus `requests` only; do not add other third-party
  dependencies without updating `setup.py`.
- All bot behavior lives on `InstaBot` with `snake_case` method names.
- Console progress uses a leading `>`, `***`, or `[*]` marker. Follow and
  unfollow status codes print as `[status_code]` with no trailing newline.
- Never hard-code usernames, passwords, or tokens in source. Credentials are
  read from `credentials.json` at runtime.
- Do not run `main.py`: it hits live Instagram endpoints and follows and
  unfollows real accounts.
- Do not commit real values to `insta_bot/credentials.json`. It ships with
  placeholders and is not excluded by `.gitignore`.

## Known rough edges (do not "fix" silently, but be aware of them)
- Stale hashes: `FOLLOWERS_QUERY_HASH`, `FOLLOWING_QUERY_HASH`, and
  `SUGGESTED_QUERY_HASH` are tied to Instagram's frontend build and can go
  stale.
- Follow loop never stops with a target: the `while ... or self.other_user`
  condition is always true, and it re-follows the same mapped list.
- Follow loop without a target: `self.foll_num` is only the `map_followers()`
  snapshot and is not increased by a follow, so `hoped_foll` does not
  measure progress. `other_user` is false here, so only that count matters.
  If the snapshot is already `>= hoped_foll`, the loop never starts.
- Unfollow loop never stops by default: `unfollow_all_not_followers` is true
  by default (`start()` and `main.py`).
- Dead unfollow cap: the 50-per-pass cap in `_unfollow_non_followers()` does
  nothing. `count = 1` is set inside the `for` loop, so `count >= 50` never
  breaks, and `count` is incremented only for accounts that already follow
  back.
- Bare `except:` in `_follow_batch` prints `> Error in suggested` and waits
  3 minutes, including on the target-follower path where the message is
  misleading.
- `map_followers()`, `map_user_followers()`, and `map_following()` read
  `self.verbose`, which only `start()` sets. Calling one before `start()`
  raises `AttributeError`.
- `login()` does not stop `start()` on authentication failure or
  `ConnectionError`. Both threads still start, and later use of
  `self.user_id` fails.
- Cache write bugs (exact-count rule, missing `has_next_page` check, wrong
  `target-followers.json` content) are described in "Data files".
