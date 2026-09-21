# Agents

This document describes the agents (automated actors) that make up InstaBot and explains how each one works, what it does, and how to configure it.

## Overview

InstaBot is composed of a single core agent class — `InstaBot` — that orchestrates two concurrent worker threads when started:

| Thread / Agent | Role |
|---|---|
| **Follow agent** | Follows new users from a target source |
| **Unfollow agent** | Unfollows users who do not follow you back |

Both threads run in parallel after `start()` is called.

---

## InstaBot (`insta_bot/src/insta_bot.py`)

The `InstaBot` class is the top-level agent. It authenticates with Instagram, gathers the data needed by the worker threads, and then launches them.

### Constructor

```python
InstaBot(username: str, password: str)
```

| Parameter | Type | Description |
|---|---|---|
| `username` | `str` | Your Instagram username |
| `password` | `str` | Your Instagram password |

### `start()`

Bootstraps everything. Call this to run the bot.

```python
bot.start(
    target_username: str = '',
    hoped_foll: int = 2000,
    unfollow_all_not_followers: bool = True,
    verbose: bool = False,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `target_username` | `str` | `''` | Instagram username whose followers will be targeted by the Follow agent. When empty, Instagram's own suggested users are used instead. |
| `hoped_foll` | `int` | `2000` | Target follower count. The Follow agent keeps running until your follower count reaches this number. |
| `unfollow_all_not_followers` | `bool` | `True` | When `True`, the Unfollow agent continues unfollowing users who don't follow you back even after your following count drops below your follower count. |
| `verbose` | `bool` | `False` | Prints each user as they are added to internal lists. |

---

## Follow Agent (`just_follow`)

The Follow agent runs in its own thread. Its job is to grow your follower count by following other accounts, which often results in them following you back.

### Behaviour

1. Determines the source of accounts to follow:
   - **Own suggested users** — used when `target_username` is not set. Calls `get_suggested_followers()` to retrieve Instagram's personalised suggestions.
   - **Followers of a target user** — used when `target_username` is set. Calls `map_user_followers()` to collect up to 1 000 followers of the specified account.
2. Iterates over the source list and calls `follow_user()` for each account.
3. If a follow request is rate-limited or rejected, the agent backs off for **10 minutes** before retrying.
4. If the suggested-users endpoint returns an error, the agent backs off for **3 minutes** before retrying.
5. Continues until your follower count reaches `hoped_foll`.

### Key methods

#### `get_suggested_followers() -> list[dict] | None`

Fetches up to 30 suggested accounts from Instagram's GraphQL API. Each entry in the returned list contains:
- `username` — the account's handle
- `id` — the account's numeric ID

Returns `None` on a non-200 response.

#### `map_user_followers(username: str, limit: int = 1000)`

Paginates through the followers of `username` and stores them in `self.user_followers`. Writes the result to `cache/target-followers.json` when the limit is reached.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `username` | `str` | — | The target Instagram account whose followers will be collected |
| `limit` | `int` | `1000` | Maximum number of followers to collect |

#### `follow_user(userid: str) -> bool`

Sends a POST request to follow the account identified by `userid`.

Returns `True` on success, `False` if the request is blocked or returns a non-200 status code.

---

## Unfollow Agent (`just_unfollow`)

The Unfollow agent runs in its own thread alongside the Follow agent. Its job is to keep your following/follower ratio healthy by unfollowing accounts that do not follow you back.

### Behaviour

1. Calls `map_followers()` and `map_following()` to build current snapshots of both lists.
2. Iterates over the accounts you are following.
3. Skips any account that appears in your followers list (mutual follow).
4. Calls `unfollow_user()` for non-mutual accounts.
5. If an unfollow request is rate-limited, the agent backs off for **10 minutes** before retrying.
6. Processes at most **50 accounts per pass**, then re-maps followers and following before starting the next pass.
7. Continues while `following_count > follower_count` or while `unfollow_all_not_followers` is `True`.

### Key methods

#### `map_followers()`

Paginates through your own followers and stores them in `self.followers`. Also records the total count in `self.foll_num`. Writes the result to `cache/followers.json`.

#### `map_following()`

Paginates through the accounts you follow and stores them in `self.following`. Also records the total count in `self.following_num`. Writes the result to `cache/following.json`.

#### `unfollow_user(userid: str) -> bool`

Sends a POST request to unfollow the account identified by `userid`.

Returns `True` on success, `False` if the request is blocked or returns a non-200 status code.

---

## Authentication

Both agents rely on an authenticated HTTP session created during `login()`.

### `login()`

1. Opens a `requests.Session` with a browser-like user-agent header.
2. Fetches the Instagram homepage to obtain a CSRF token.
3. POSTs credentials to the AJAX login endpoint using an encrypted password format (`generate_encrypted_password()`).
4. Stores the session-level CSRF token and the authenticated user ID on the instance.

### `get_userid(username: str) -> str | None`

Resolves an Instagram username to its numeric user ID by querying the public profile endpoint. Returns `None` if the request fails.

---

## Cache

Intermediate results are persisted to JSON files under `insta_bot/cache/` so that the agent can resume without re-fetching data on a restart.

| File | Written by | Contents |
|---|---|---|
| `cache/followers.json` | `map_followers()` | Your own followers |
| `cache/following.json` | `map_following()` | Accounts you follow |
| `cache/target-followers.json` | `map_user_followers()` | Followers of the target account |

---

## Configuration

Credentials and the target username are read from `insta_bot/credentials.json`:

```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "some.account"
}
```

Leave `target_username` as an empty string to use Instagram's suggested users instead of a specific account's followers.

---

## Rate limiting

Both agents implement back-off on failure:

| Situation | Back-off |
|---|---|
| Follow or unfollow request blocked / non-200 | 10 minutes |
| Suggested-users endpoint error | 3 minutes |

Instagram aggressively rate-limits automated activity. Running the bot at high frequency risks a temporary or permanent account ban.
