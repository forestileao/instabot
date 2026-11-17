# AGENTS.md

## Project overview

Insta Bot automates Instagram follow/unfollow through the website's private
`graphql` and `web/friendships` endpoints, not the official API. It logs in
with a username and password, starts two background threads, and returns.
- Follow thread: follows a target account's followers when `target_username`
  is non-empty; otherwise follows Instagram's suggested users (it still maps
  the logged-in account's followers, but does not follow that list).
- Unfollow thread: unfollows accounts you follow that do not follow you back.

`main.py` passes only `target_username` and `verbose=False`, so `hoped_foll`
stays 2000 and `unfollow_all_not_followers` stays true. Those defaults do
not stop either loop (see "Known rough edges").

## Tech stack

- Python 3 with the `requests` library only.
- Instagram private API emulated through `graphql` queries and `web/friendships`
  endpoints.

## Repository layout

```
insta_bot/
├── __init__.py
├── credentials.json        # placeholders; not excluded by .gitignore
├── main.py
└── src/
    ├── __init__.py
    └── insta_bot.py
tests/
└── test_insta_bot.py
setup.py
```

- The `src` import path is not installed (`setup.py` installs `insta_bot` only,
  not `insta_bot.src`).
- `.gitignore` lists `target-followes.json` (intentional typo, keep it).
  `target-followers.json` is not ignored.

## Setup and run steps

Commands and imports expect the process to start in `insta_bot/`. Both
`from src.insta_bot import InstaBot` and the open of `./credentials.json`
are relative to that directory. Cache files are written from the source file
location, not the process cwd.

Do not run `main.py`: it hits live Instagram endpoints and follows and
unfollows real accounts.

## Conventions for agents

- Standard library plus `requests` only; do not add other third-party
  dependencies without updating `setup.py`.
- All bot behavior lives on `InstaBot` with `snake_case` method names.
- Console progress uses a leading `>`, `***`, or `[*]` marker.
- Never hard-code usernames, passwords, or tokens in source. Credentials are
  read from `credentials.json` at runtime.
- Do not commit real values to `insta_bot/credentials.json`. It ships with
  placeholders and is not excluded by `.gitignore`.
- Reuse constants and helpers. Do not re-inline them.
- `_connection_url` must stay a compact variables string. Do not switch it
  to `json.dumps`. Suggested-user requests keep `json.dumps`.
- A cache file is written only when the collected count exactly equals the
  stop count. There is no next-page check. `target-followers.json` is dumped
  from `self.followers`, not `self.user_followers`.
- Follow and unfollow status lines print as `[status_code]` with no trailing
  newline.

## Known issues

Do not fix these unless the task says so.
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
- Login prints `> Erron on login authentication`. Keep the `Erron` typo; do
  not correct it.
- Cache writes (exact-count rule, no next-page check, `target-followers.json`
  dumped from `self.followers`) are not to be fixed unless the task says so.

## Testing and verification

There are no linters and no CI. These offline checks need no credentials or
network, only `requests` installed. Run them from the repository root:
```sh
python3 -m py_compile insta_bot/main.py insta_bot/src/insta_bot.py
cd insta_bot && python3 -c "from src.insta_bot import InstaBot"
python3 tests/test_insta_bot.py
```
`tests/test_insta_bot.py` inserts the package directory on `sys.path`
itself, so do not prescribe `python3 -m unittest`.