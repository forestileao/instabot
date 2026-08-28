# Insta Bot v1.0.0 - By ForestiLeao

### Requirements
 - Python3
 - Python requests module (installed in the next section)

### Download
To Download the instagram bot, just execute the command in your terminal:
```sh
$ git clone https://github.com/forestileao/instabot.git
$ cd instabot
$ pip3 install -e . # This command will install the request lib
```

### Simple usage
Copy `insta_bot/credentials.example.json` to `insta_bot/credentials.json` and fill in your
credentials and the target username that you want to map its followers:
```sh
$ cp insta_bot/credentials.example.json insta_bot/credentials.json
```
```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "john.doe"
}
```
`insta_bot/credentials.json` holds real secrets and is listed in `.gitignore`, so it will
never be committed. Then, from the repository root, execute main.py and the standard bot
commands will be executed.
```sh
$ python3 insta_bot/main.py
```

