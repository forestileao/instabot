import json
from os import path

from insta_bot.src.insta_bot import InstaBot


if __name__ == "__main__":
    credentials_path = path.join(path.dirname(__file__), 'credentials.json')
    with open(credentials_path) as json_file:
        cred = json.load(json_file)
        bot = InstaBot(username=cred['username'], password=cred['password'])
    bot.start(target_username=cred['target_username'], verbose=False)
