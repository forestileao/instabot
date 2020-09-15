from src.insta_bot import InstaBot


if __name__ == "__main__":
    bot = InstaBot(username='cbbottest', password='thisiscrazy')
    bot.login()
    bot.map_followers()
    bot.start()

