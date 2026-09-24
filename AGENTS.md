# AGENTS.md

## Overview
Insta Bot is a small Python script that automates Instagram follow/unfollow
activity through Instagram's private web endpoints (the same `graphql` and
`web/friendships` calls the website itself uses, not the official API). It
logs in with a username and password, maps the followers of a target user
(or, if no target is given, uses Instagram's "suggested users" list), and
then runs two background threads: one that follows users from that mapped
list until a follower goal is reached, and one that unfollows accounts you
follow that don't follow you back.

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
  the single runtime dependency `requests~=2.24.0`.
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
   that directory):
   ```sh
   cd insta_bot
   python3 main.py
   ```

## Key behaviors (in `src/insta_bot.py`)
- `login()` - opens a `requests.Session`, grabs a CSRF token from
  instagram.com, encrypts the password with `generate_encrypted_password()`
  (a `#PWD_INSTAGRAM_BROWSER:...` string, not real encryption), and posts to
  `/accounts/login/ajax/`. Prints the logged-in user id/username or an
  error, and stores `self.user_id`.
- `get_userid(username)` - resolves a username to its numeric id via the
  `?__a=1` endpoint.
- `map_followers()` / `map_user_followers(username, limit=1000)` - page
  through the `edge_followed_by` GraphQL query (hard-coded `query_hash`) to
  build `self.followers` / `self.user_followers`, then dump a snapshot to
  the `cache/` folder as JSON (`cache/followers.json` /
  `cache/target-followers.json`; see "Known rough edges" below for a bug in
  what `map_user_followers` actually writes).
- `map_following()` - same pattern using the `edge_follow` query hash to
  build `self.following` and write `cache/following.json`.
- `get_suggested_followers()` - calls the suggested-users GraphQL query and
  returns a list of `{username, id}` candidates.
- `follow_user(userid)` / `unfollow_user(userid)` - POST to
  `/web/friendships/{id}/follow/` or `/unfollow/`. Print a `[status_code]`
  marker and return `True`/`False` based on the response.
- `just_follow()` - loop used by the follow thread: maps followers (target
  user's, or self via suggestions if no target), then repeatedly follows
  users until `hoped_foll` is reached (or forever if `other_user` is set).
  On errors it prints a message and sleeps.
- `just_unfollow()` - loop used by the unfollow thread: maps followers and
  following, then unfollows anyone you follow who isn't in your followers
  list, re-mapping between passes. Intended to cap each pass at 50
  unfollows, but see "Known rough edges" - that cap does not currently
  work.
- `start(target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False)`
  - sets instance flags, calls `login()`, then starts `just_follow` and
    `just_unfollow` each on its own `Thread`. With the default arguments
    both threads loop indefinitely: `just_follow` never stops once
    `target_username` is set (its exit condition is a `hoped_foll` OR
    `other_user`, and `other_user` is `True` whenever a target is given),
    and `just_unfollow` never stops while `unfollow_all_not_followers`
    stays `True` (also the default).

## Data files
- Mapped lists are written as JSON under `insta_bot/cache/`:
  `followers.json`, `following.json`, and `target-followers.json`.
- The `.gitignore` lists similarly named files at the repo root
  (`followers.json`, `following.json`, `target-followes.json`, note the
  typo) so generated data is not committed.

## Conventions
- Standard library plus `requests` only; no other third-party
  dependencies are used or should be added without updating `setup.py`.
- All bot behavior lives on the `InstaBot` class using `snake_case` method
  names (`map_followers`, `follow_user`, `just_unfollow`, etc.).
- Console progress is printed with a leading `>` or `***`/`[*]` marker
  (e.g. `> Followed {username}`, `*** Mapping followers ***`).
- Credentials are always read from `credentials.json` at runtime; never
  hard-code usernames, passwords, or tokens in source.

## Known rough edges (do not "fix" silently, but be aware of them)
- GraphQL `query_hash` values are hard-coded strings tied to Instagram's
  current frontend build; they can go stale if Instagram changes them.
- Several loops use bare/broad `except:` blocks (e.g. in `just_follow`)
  that swallow all errors and just sleep and retry.
- `credentials.json` ships with placeholder values and is not excluded by
  `.gitignore`, so real credentials should not be committed here.
- `map_user_followers()` writes `self.followers` (the *self* follower
  list) to `cache/target-followers.json` instead of the `self.user_followers`
  list it just built - likely a copy/paste bug, so that cache file does not
  actually reflect the target account's followers.
- The 50-unfollow-per-pass cap in `just_unfollow()` is dead code: `count`
  is reset to `1` at the top of every loop iteration instead of being
  initialized once before the loop, so `if count >= 50: break` never
  fires as intended.
- `start()`'s defaults (`unfollow_all_not_followers=True`, and
  `other_user=True` whenever `target_username` is set) mean the exit
  conditions in `just_follow`/`just_unfollow` are effectively always true,
  so both background threads run indefinitely rather than stopping once a
  goal is met.
