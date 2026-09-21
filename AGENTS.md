# AGENTS.md

Guidance for coding agents working in the `instabot` repository.

## Overview

`instabot` (package name `insta-bot`, version `1.0.0`) is a small Python
Instagram bot. It logs into Instagram with a username/password, follows the
followers of a chosen target account (or Instagram's suggested users if no
target is given), and unfollows accounts that don't follow back. It is
packaged with `setuptools` and depends only on `requests`.

## Project structure

```
.
├── AGENTS.md
├── README.md
├── setup.py                  # setuptools packaging (name=insta-bot, version=1.0.0)
└── insta_bot/
    ├── __init__.py
    ├── credentials.json      # login + target config (placeholder values, do not commit real secrets)
    ├── main.py                # entry point script
    ├── cache/                 # JSON output written at runtime (gitignored)
    │   └── .gitkeep
    └── src/
        ├── __init__.py
        └── insta_bot.py       # InstaBot class with all bot logic
```

## Setup

Requirements: Python 3 and pip.

```sh
git clone https://github.com/forestileao/instabot.git
cd instabot
pip3 install -e .
```

This installs the single dependency declared in `setup.py`:
`requests~=2.24.0`.

## Configuration

Edit `insta_bot/credentials.json` before running the bot:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "john.doe"
}
```

- `username` / `password`: the Instagram account the bot logs in as.
- `target_username`: optional. If set, the bot follows that account's
  followers. If left empty (`""`), the bot follows Instagram's suggested
  users instead.

Never commit real credentials; the checked-in file only holds placeholders.

## Running

`insta_bot/main.py` opens `./credentials.json` (a relative path) and imports
`src.insta_bot`, so it must be run from inside the `insta_bot/` directory:

```sh
cd insta_bot
python3 main.py
```

`main.py` reads `credentials.json`, constructs `InstaBot(username, password)`,
and calls `bot.start(target_username=cred['target_username'], verbose=False)`.

## Key modules

`insta_bot/src/insta_bot.py` defines the `InstaBot` class:

- `login()` — authenticates against Instagram's ajax login endpoint and
  stores an authenticated `requests.Session`.
- `get_userid(username)` — resolves a username to its numeric Instagram id.
- `map_user_followers(username, limit=1000)` — fetches followers of a target
  user, writing results to `insta_bot/cache/target-followers.json`.
- `map_followers()` — fetches the logged-in account's followers, writing
  results to `insta_bot/cache/followers.json`.
- `map_following()` — fetches accounts the logged-in account follows, writing
  results to `insta_bot/cache/following.json`.
- `follow_user(userid)` / `unfollow_user(userid)` — perform follow/unfollow
  requests.
- `get_suggested_followers()` — fetches Instagram's suggested users list.
- `just_follow()` — follows either the target's followers or suggested users
  in a loop until `hoped_foll` is reached.
- `just_unfollow()` — unfollows accounts that are followed but do not follow
  back.
- `start(target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False)`
  — logs in, then runs `just_follow()` and `just_unfollow()` concurrently on
  separate threads. This is the method called from `main.py`.

## Cache output files

All cache files are written relative to `insta_bot/src/insta_bot.py` via
`path.dirname(__file__)+'/../cache/'`, i.e. into `insta_bot/cache/`:

- `insta_bot/cache/followers.json`
- `insta_bot/cache/following.json`
- `insta_bot/cache/target-followers.json`

These are runtime-generated data files (ignored by `.gitignore`) and should
not be committed.

## Conventions

- Keep the single external dependency limited to `requests` unless `setup.py`
  is intentionally updated.
- Bot logic lives in `insta_bot/src/insta_bot.py`; `insta_bot/main.py` should
  stay a thin entry point that loads `credentials.json` and calls
  `InstaBot.start(...)`.
- Do not commit real Instagram credentials or generated cache files.
