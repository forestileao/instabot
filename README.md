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
 Put your credentials and the target username that you want to map its followers in credentials.json, located in the insta_bot package. Like this example:
```json
{
    "username": "your_username",
    "password": "your_password",
    "target_username": "john.doe"
}
  ```
Then, execute main.py and the standard bot commands will be executed.
```sh
$ python3 main.py
```

