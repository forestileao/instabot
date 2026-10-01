import json
from src.insta_bot import InstaBot


CREDENTIALS_PATH = './credentials.json'


def load_credentials(credentials_path=CREDENTIALS_PATH):
    with open(credentials_path) as json_file:
        return json.load(json_file)


def main():
    credentials = load_credentials()
    bot = InstaBot(username=credentials['username'], password=credentials['password'])
    bot.start(target_username=credentials['target_username'], verbose=False)


if __name__ == '__main__':
    main()
