# Insta Bot

## Requirements

- Python 3

## Install

From the repository root, install the package so `setup.py` installs `requests`:

```sh
pip3 install -e .
```

## Credentials

Fill `insta_bot/credentials.json` with `username`, `password`, and `target_username`. Use placeholders only:

```json
{
  "username": "your_username",
  "password": "your_password",
  "target_username": "target_username"
}
```

## Run

Change to `insta_bot/` before starting. That directory is required because `main.py` imports `src.insta_bot` and opens `./credentials.json`.

```sh
cd insta_bot
python3 main.py
```

The process logs into Instagram and follows and unfollows real accounts.
