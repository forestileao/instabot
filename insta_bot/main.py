import json
import logging
import os

from insta_bot import InstaBot

CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')


def load_credentials(path=CREDENTIALS_PATH):
    with open(path) as json_file:
        return json.load(json_file)


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    credentials = load_credentials()
    bot = InstaBot(username=credentials['username'], password=credentials['password'])
    bot.start(target_username=credentials.get('target_username', ''), verbose=False)


if __name__ == '__main__':
    main()
