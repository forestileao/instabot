import json
from src.insta_bot import InstaBot


if __name__ == "__main__":
    with open('./credentials.json') as json_file:
        cred = json.load(json_file)
        bot = InstaBot(username=cred['username'], password=cred['password'], target_username=cred['user_target'])
    bot.start()
