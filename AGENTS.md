# AGENTS.md

## Overview
Insta Bot is a small Python script that automates Instagram follow/unfollow
activity through Instagram's private web endpoints (the same `graphql` and
`web/friendships` calls the website itself uses, not the official API). It
logs in with a username and password, then starts two background threads
and returns. The follow thread follows a target account's followers when
`target_username` is non-empty; otherwise it follows Instagram's suggested
users (it still maps the logged-in account's followers, but does not follow
that list). The unfollow thread unfollows accounts you follow that do not
follow you back. `main.py` only passes `target_username` and
`verbose=False`, so `hoped_foll` stays `2000` and
`unfollow_all_not_followers` stays `True`. Those defaults do not stop
either thread. See "Known rough edges".

## Layout
- `insta_bot/` - the Python package.
  - `main.py` - entry point. Reads credentials through `load_credentials()`
    and `CREDENTIALS_PATH`. That path is still `./credentials.json` and is
    still relative to the working directory. Builds an `InstaBot` and calls
    `bot.start(target_username=..., verbose=False)`.
  - `credentials.json` - holds `username`, `password`, and
    `target_username`. Read at runtime; not meant to contain real secrets in
    version control. The committed file uses placeholders and an empty
    `target_username`.
  - `src/insta_bot.py` - all bot logic lives in the `InstaBot` class here,
    plus module constants and private helpers. Copy those; do not re-inline
    them.
  - `src/__init__.py`, `insta_bot/__init__.py` - empty package markers.
  - `cache/` - output folder for the JSON files the bot writes while
    mapping followers/following (contains only `.gitkeep` in the repo).
- `tests/test_insta_bot.py` - automated tests. Inserts the `insta_bot/`
  package directory on `sys.path`, then imports `src.insta_bot` and `main`.
  Run it as a script from the repository root (see "Checking changes").
- `setup.py` - packaging metadata (`insta-bot`, version `1.0.0`), declares
  the single runtime dependency `requests~=2.24.0`. `packages` lists only
  `insta_bot`, not `insta_bot.src`, so the `src` import path is not
  installed.
- `README.md` - short install/usage instructions for end users.
- `.gitignore` - ignores `*.egg`, `*.egg-info`, `__pycache__`, `venv`, and
  the generated `followers.json`, `following.json`, `target-followes.json`
  (note the existing typo, kept as-is).

The import `from src.insta_bot import InstaBot` still requires a run from
`insta_bot/`.

## Setup and run
1. Requires Python 3.
2. From the repository root, install the package in editable mode; this
   pulls in `requests` per `setup.py`:
   ```sh
   pip3 install -e .
   ```
3. Edit `insta_bot/credentials.json` and fill in `username`, `password`,
   and (optionally) `target_username`. An empty `target_username` (the
   committed value) selects the suggested-users follow path. A non-empty
   value selects that account's followers.
4. Run the entry point from inside the `insta_bot/` package folder. The
   import `from src.insta_bot import InstaBot` and the open of
   `./credentials.json` (`CREDENTIALS_PATH`) are both relative to that
   working directory:
   ```sh
   cd insta_bot
   python3 main.py
   ```

## Checking changes
The repo has no linters and no CI. Automated tests live in
`tests/test_insta_bot.py`. Use these offline checks, which need no
credentials or network access:
```sh
python3 -m py_compile insta_bot/main.py insta_bot/src/insta_bot.py
cd insta_bot && python3 -c "from src.insta_bot import InstaBot"
python3 tests/test_insta_bot.py
```
Run them from the repository root. `tests/test_insta_bot.py` inserts the
package directory on `sys.path`, so do not prescribe `python3 -m unittest`.
The import check and the tests need `requests` installed (see "Setup and
run").

Running `main.py` hits live Instagram endpoints with real credentials and
follows/unfollows real accounts. Do not run it, and do not commit real
values to `insta_bot/credentials.json`.

## Key behaviors (in `src/insta_bot.py`)
Module constants (copy these; do not inline the values):
- `FOLLOWERS_QUERY_HASH` is `c76146de99bb02f6415203be841dd25a`.
- `FOLLOWING_QUERY_HASH` is `d04b0a864b4b54837c0d870b0e77e076`.
- `SUGGESTED_QUERY_HASH` is `ed2e3ff5ae8b96717476b62ef06ed8cc`.
- `FOLLOWERS_PAGE_SIZE` is 24. `FOLLOWERS_NEXT_PAGE_SIZE` is 12.
  `FOLLOWING_PAGE_SIZE` is 24.
- `RATE_LIMIT_PREFIX` is `Ple`. `RATE_LIMIT_WAIT_SECONDS` is `10 * 60`
  (600). `SUGGESTED_ERROR_WAIT_SECONDS` is `3 * 60` (180).
  `INSTAGRAM_DESCRIPTION_PREFIX` is `Ins`.
- `SUGGESTED_QUERY` is the suggested-users variables dict in source.
  Suggested-user requests still use `json.dumps(SUGGESTED_QUERY)`.

Private helpers (call these; do not re-inline them):
- `_set_csrf` sets `x-csrftoken` from the response cookie after the home
  GET and again after the login POST.
- `_get_json` loads a GET body as JSON.
- `_connection_url` builds a compact variables string with no spaces. Do
  not switch it to `json.dumps`. Suggested users still use
  `json.dumps(SUGGESTED_QUERY)`.
- `_user_record` returns `{username, id}`.
- `_write_cache` writes `path.dirname(__file__) + '/../cache/' + filename`.
- `_friendship_action` owns the follow and unfollow POSTs. It prints
  `[status_code]` with no newline. It returns `False` when the status is
  not 200 or the body starts with `Ple`.
- `_suggested_users` skips descriptions whose first three characters are
  `Ins`.
- `_follow_batch` owns the bare `except`. It prints `> Error in suggested`
  and sleeps `SUGGESTED_ERROR_WAIT_SECONDS`. `just_follow` calls it with
  `get_suggested_followers` or with a lambda that returns
  `self.user_followers`.
- `_follow_one` prints `> Followed {username}` or waits
  `RATE_LIMIT_WAIT_SECONDS`.
- `_unfollow_non_followers` holds the dead `count = 1` and `count >= 50`
  logic.
- `_unfollow_until_success` retries the same user.

Public methods:
- `login()` - opens a `requests.Session`, sets a hard-coded user agent and
  `Referer`, GETs `https://www.instagram.com` for a `csrftoken` cookie, and
  posts `username` plus `generate_encrypted_password()` to
  `/accounts/login/ajax/`. `_set_csrf` runs after the home GET and again
  after the login POST. The password string is
  `#PWD_INSTAGRAM_BROWSER:0:{unix_time}:{plaintext}`, not real encryption.
  On `authenticated`, it stores `self.user_id` and prints
  `> Logged in (user:..., id:...)`. Otherwise it prints
  `> Erron on login authentication` (typo in source) and the parsed body,
  and does not set `self.user_id`. A `requests.exceptions.ConnectionError`
  prints `> Connection refused`. `login()` returns the parsed body after a
  completed request, or `None` on `ConnectionError`. `start()` does not
  check the result and still starts both threads.
- `get_userid(username)` - GET `https://instagram.com/{username}/?__a=1`
  (no `www`). Returns the GraphQL user id on status 200, otherwise `None`.
- `map_followers()` - pages `edge_followed_by` with `FOLLOWERS_QUERY_HASH`
  (`first` `FOLLOWERS_PAGE_SIZE`, then `FOLLOWERS_NEXT_PAGE_SIZE`) via
  `_connection_url` and `_get_json` into `self.followers` (`_user_record`)
  and sets `self.foll_num` from the first page's `count`. Writes
  `cache/followers.json` through `_write_cache` only when the collected
  `count` equals `self.foll_num`. A `status == fail` response breaks
  without writing. Reads `self.verbose` for per-user prints.
- `map_user_followers(username, limit=1000)` - same query hash, for
  `get_userid(username)`, into `self.user_followers`. Sets
  `self.user_foll_num` from the first page. Stops and writes
  `cache/target-followers.json` through `_write_cache` only when
  `count == limit`, and the file is `self.followers`, not
  `self.user_followers`. A `status == fail` break skips the write. Reads
  `self.verbose`.
- `map_following()` - pages `edge_follow` with `FOLLOWING_QUERY_HASH`
  (`first` `FOLLOWING_PAGE_SIZE` on every page) into `self.following` and
  sets `self.following_num`. Writes `cache/following.json` through
  `_write_cache` only when `count == self.following_num`. A
  `status == fail` break skips the write. Reads `self.verbose`.
- `get_suggested_followers()` - suggested-users query hash
  `SUGGESTED_QUERY_HASH` and `json.dumps(SUGGESTED_QUERY)`.
  `_suggested_users` skips nodes whose `description` starts with `Ins`.
  Returns `{username, id}` dicts, or `None` if the status is not 200.
- `follow_user(userid)` / `unfollow_user(userid)` - call
  `_friendship_action` for `/web/friendships/{id}/follow/` or
  `/unfollow/`. Print `[status_code]` with no newline. Return `False` when
  the status is not 200 or the body starts with `Ple` (rate-limit text);
  otherwise `True`.
- `just_follow()` - follow-thread loop.
  - No target (`other_user` is false): `map_followers()`, then while
    `self.foll_num < self.hoped_foll or self.other_user` call
    `_follow_batch(self.get_suggested_followers)`. `other_user` is false on
    this path, so only the count check matters, and `foll_num` is not
    updated after a follow. The comparison is against the initial follower
    count only.
  - Target set (`other_user` is true): `map_user_followers(target)` once,
    then while `self.user_foll_num < self.hoped_foll or self.other_user`
    call `_follow_batch` with a lambda that returns `self.user_followers`.
    Because `other_user` is true, this loop does not end.
  - A failed follow is `_follow_one`: it prints
    `> Waiting 10 min until next FOLLOW request` and sleeps
    `RATE_LIMIT_WAIT_SECONDS`, then moves on. The bare `except` is in
    `_follow_batch`: it prints `> Error in suggested` and sleeps
    `SUGGESTED_ERROR_WAIT_SECONDS` (including when the suggested call
    returns `None`).
- `just_unfollow()` - unfollow-thread loop. Maps followers and following,
  then while `self.following_num > self.foll_num or
  self.unfollow_all_not_followers` calls `_unfollow_non_followers`, then
  maps again. That helper unfollows each followed account whose
  `{username, id}` dict is not in `self.followers`, via
  `_unfollow_until_success`. The default flag is true, so the loop does
  not end. A failed unfollow sleeps `RATE_LIMIT_WAIT_SECONDS` and retries
  that same user. There is no `try`/`except` here; an error kills the
  thread. The `count >= 50` break in `_unfollow_non_followers` does not
  work (see below).
- `start(target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False)`
  - sets `self.unfollow_all_not_followers`, `self.verbose`, and
    `self.hoped_foll`. Sets `self.other_user` to `False`, then sets
    `self.target_username` and `self.other_user` to `True` only when
    `len(target_username) > 0`. Calls `login()`, then starts `just_follow`
    and `just_unfollow` on non-daemon `Thread`s and returns without joining
    them. A failed login or `ConnectionError` still starts both threads.
    The two threads share one `requests.Session` with no lock.

## Data files
- Cache paths are built by `_write_cache` as
  `path.dirname(__file__) + '/../cache/' + filename` from
  `src/insta_bot.py`, so they resolve to `insta_bot/cache/` regardless of
  the process cwd: `followers.json`, `following.json`, and
  `target-followers.json`.
- A file is written only when the page loop's collected count exactly
  equals its stop value. There is no `has_next_page` check. An early
  `status == fail` skips the write.
- `target-followers.json` is dumped from `self.followers`, not from the
  `self.user_followers` list just built. It is not the target account's
  followers.
- `.gitignore` lists `followers.json`, `following.json`, and the misspelled
  `target-followes.json`. Those names match in any directory.
  `target-followers.json` is not ignored.

## Conventions
- Standard library plus `requests` only; no other third-party
  dependencies are used or should be added without updating `setup.py`.
- All bot behavior lives on the `InstaBot` class using `snake_case` method
  names (`map_followers`, `follow_user`, `just_unfollow`, etc.).
- Console progress uses a leading `>`, `***`, or `[*]` marker
  (e.g. `> Followed {username}`, `*** Mapping followers ***`,
  `[*] Followers:`). Follow and unfollow status codes print as
  `[status_code]` with no trailing newline.
- Credentials are always read from `credentials.json` at runtime; never
  hard-code usernames, passwords, or tokens in source.
- Do not run `main.py`. It performs real follows and unfollows.

## Known rough edges (do not "fix" silently, but be aware of them)
- GraphQL `query_hash` values (`FOLLOWERS_QUERY_HASH`,
  `FOLLOWING_QUERY_HASH`, `SUGGESTED_QUERY_HASH`) are hard-coded strings
  tied to Instagram's current frontend build; they can go stale if
  Instagram changes them.
- `_follow_batch` (called from `just_follow` on both paths) uses a bare
  `except:` that prints `> Error in suggested` and sleeps
  `SUGGESTED_ERROR_WAIT_SECONDS` (3 minutes). That message is also used on
  the target-follower path.
- `credentials.json` ships with placeholder values and is not excluded by
  `.gitignore`, so real credentials should not be committed here.
- `map_user_followers()` writes `self.followers` to
  `cache/target-followers.json` instead of `self.user_followers`.
- Cache writes and loop exits in the three map methods require an exact
  count match (`count == self.foll_num`, `count == limit`, or
  `count == self.following_num`). A short last page or a total that the
  edges never hit can skip the write and keep paging until `status == fail`
  or an uncaught error.
- With a target, `just_follow()` is `while ... or self.other_user`, so it
  never stops, and it re-follows the same mapped list. Without a target,
  `self.foll_num` is only the `map_followers()` snapshot and is not
  increased when a follow succeeds, so `hoped_foll` does not measure
  progress. If that snapshot is already `>= hoped_foll`, the follow loop
  never starts.
- The 50-per-pass cap in `_unfollow_non_followers()` (called from
  `just_unfollow()`) is dead code. `count = 1` is inside the `for` loop,
  so `count >= 50` never breaks, and `count` is incremented only for
  accounts that already follow back. The `while` stays true while
  `unfollow_all_not_followers` is true, which is the default `start()`
  uses and the value `main.py` leaves in place, so the unfollow loop does
  not end by default.
- `map_followers()`, `map_user_followers()`, and `map_following()` read
  `self.verbose`, which only `start()` sets. Calling a map method before
  `start()` raises `AttributeError`.
- `login()` does not stop `start()` on authentication failure or
  `ConnectionError`. Both threads still start. Later use of `self.user_id`
  then fails.
