# AGENTS.md

Context file for coding agents working on the `instabot` repository.

---

## Project purpose

Python 3 Instagram automation bot. It logs in via the private Instagram web API,
maps the logged-in user's followers and following lists, follows suggested users or
the followers of a chosen target account, and unfollows users who do not follow back.
The `follow` and `unfollow` actions run concurrently in two `threading.Thread` threads
started from `InstaBot.start()`.

---

## Stack

| Component      | Detail                                              |
|----------------|-----------------------------------------------------|
| Language       | Python 3                                            |
| HTTP client    | `requests ~= 2.24.0` (only external dependency)    |
| Concurrency    | `threading.Thread` (two threads: follow + unfollow) |
| Standard libs  | `json`, `time`, `os.path`                           |
| Entry point    | `insta_bot/main.py`                                 |
| Package config | `setup.py` (setuptools)                             |

---

## Directory layout

```
instabot/                    # repository root
  AGENTS.md                  # this file
  README.md
  setup.py                   # declares requests~=2.24.0
  .gitignore
  insta_bot/
    __init__.py
    credentials.json         # runtime credentials – must be filled in; not committed
    cache/                   # JSON caches written at runtime (followers, following, target-followers)
    main.py                  # entry point; MUST be run from inside insta_bot/
    src/
      __init__.py
      insta_bot.py           # InstaBot class; all bot logic lives here
```

---

## Setup

1. **Install dependencies** from the repository root:

   ```sh
   pip3 install -e .
   ```

   This installs `requests ~= 2.24.0` as declared in `setup.py`.

2. **Fill in credentials** at `insta_bot/credentials.json`:

   ```json
   {
     "username": "your_username",
     "password": "your_password",
     "target_username": "john.doe"
   }
   ```

   - `username` / `password` — the Instagram account the bot will act as.
   - `target_username` — the account whose followers the bot will follow
     (passed to `InstaBot.start()` as `target_username`).

---

## Run

Change into `insta_bot/` before running:

```sh
cd insta_bot
python3 main.py
```

`main.py` opens `./credentials.json` with a relative path and imports `src.insta_bot`
without a package prefix. Both assumptions break if the script is run from any
directory other than `insta_bot/`.

---

## Known bugs (do not fix here — fix in a dedicated task)

The following bugs exist in the current source at `insta_bot/src/insta_bot.py`.
They are documented so a later agent can fix them deliberately.

1. **`map_user_followers` writes the wrong variable to cache** (line 102)

   ```python
   json.dump(self.followers, outfile)   # BUG: should be self.user_followers
   ```

   The cache file `cache/target-followers.json` is always written with the
   logged-in user's own followers instead of the target account's followers.

2. **`map_user_followers` references `self.verbose` before it is set** (line 91)

   `self.verbose` is only assigned inside `start()`. Calling `map_user_followers`
   directly before `start()` raises `AttributeError: 'InstaBot' object has no
   attribute 'verbose'`.

3. **`just_follow` loop condition uses `or` instead of `and`** (lines 233 and 248)

   ```python
   while self.foll_num < self.hoped_foll or self.other_user:   # BUG
   while self.user_foll_num < self.hoped_foll or self.other_user:  # BUG
   ```

   When `self.other_user` is `True` (i.e. a `target_username` was supplied),
   the loop never exits because the `or` condition is always satisfied. The
   intent is `and`.

4. **`just_unfollow` resets `count` to `1` inside the loop** (line 269)

   ```python
   for following in self.following:
       count = 1          # BUG: reset every iteration
       if count >= 50:    # this branch is never reached
           break
   ```

   `count` is re-initialised to `1` at the start of every iteration, so the
   `count >= 50` guard never fires. All non-followers are unfollowed in a
   single pass regardless of the intended 50-unfollow batch limit.

5. **`map_following` has a tab/space indentation mix** (line 168)

   ```python
   for user in foll_req_list['data']['user']['edge_follow']['edges']:
       self.following.append({
           'username':user['node']['username'],
           'id':user['node']['id']
   	})            # <-- line 168: leading TAB instead of spaces
   ```

   The closing `})` is indented with a tab while the rest of the block uses
   spaces. This can cause `IndentationError` in some Python environments or
   editors that enforce strict whitespace consistency.

6. **Instagram private API endpoints are unofficial and may no longer work**

   The bot calls undocumented GraphQL endpoints with `?__a=1` and
   `query_hash=...` parameters. Instagram has rate-limited or blocked these
   endpoints. The bot may fail silently or produce HTTP errors against the live
   API without updates to the endpoint URLs or authentication flow.

---

## Conventions an agent must follow

- Always run `main.py` from **inside `insta_bot/`**, not from the repository root.
- Do **not** commit `credentials.json`. It is not currently listed in `.gitignore`
  by name (only the cache JSON files are); add it to `.gitignore` if needed.
- There are no automated tests. Verify behavior by reading the source and, where
  safe, running the bot against a dedicated test account.
- Do not change `README.md` or any existing source file unless the task
  explicitly targets that file.
