# Insta Bot

Insta Bot automates Instagram following and unfollowing using the website's
private `graphql` and `web/friendships` endpoints, rather than the official API.
Starting the program logs in and performs real account actions.

## Requirements

- Python 3
- `pip3` for installation
- `requests~=2.24.0`, declared in [setup.py](setup.py) and installed by the command below
- An Instagram account and an internet connection for live use

## Install

From the repository root, install the package so `setup.py` installs `requests`:

```sh
pip3 install -e .
```

## Credentials

Edit [insta_bot/credentials.json](insta_bot/credentials.json) with the three keys
below. The example contains placeholders; replace them locally with your account
details and the desired target:

```json
{
  "username": "your_username",
  "password": "your_password",
  "target_username": "target_username"
}
```

- A nonempty `target_username` selects that account's followers to follow.
- Set `"target_username": ""` to follow Instagram's suggested accounts instead.

The credential file is tracked by Git and is not ignored. Do not commit real
usernames or passwords.

## Run

Change to `insta_bot/` before starting. That directory is required because `main.py` imports `src.insta_bot` and opens `./credentials.json`.
The editable installation does not remove this source-directory requirement:
`setup.py` installs `insta_bot`, but not the `src` import path used by the entry point.

```sh
cd insta_bot
python3 main.py
```

## Operating behavior and limitations

[main.py](insta_bot/main.py) starts two concurrent background workers:

- **Follow:** follows the target account's followers, or suggested accounts when
  the target is empty. In suggested mode it also maps your own followers, but
  does not use that list as the accounts to follow.
- **Unfollow:** maps your followers and the accounts you follow, then unfollows
  accounts that do not follow you back.

The implementation in [insta_bot.py](insta_bot/src/insta_bot.py) has important
limitations:

- Private endpoints and their query hashes may be stale. Compatibility with live
  Instagram has not been verified.
- The follower goal (`hoped_foll`, default `2000`) does not reliably stop the
  follow loop. With a target, the loop keeps reusing the mapped list; without a
  target, its follower count is a snapshot that is not increased after following.
- The default unfollow loop continues because `unfollow_all_not_followers` is
  `True`. `main.py` leaves both this setting and the follower goal at their defaults.
- Failed authentication or a caught connection error does not prevent worker
  startup; the workers can subsequently fail because no user ID was set.

## Offline checks

With `requests` installed, run these checks from the repository root. They need
neither credentials nor network access and do not start the live bot:

```sh
python3 -m py_compile insta_bot/main.py insta_bot/src/insta_bot.py
(cd insta_bot && python3 -c "from src.insta_bot import InstaBot")
python3 tests/test_insta_bot.py
```

The subshell keeps the final command in the repository root. The test script sets
its own import path. These checks verify local code behavior, not compatibility
with live Instagram.
