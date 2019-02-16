from src import KarmaBot

if __name__ == '__main__':
    karma_bot = KarmaBot(
        'mm_access_token',
        'mm_wss_url')
    karma_bot.wake_up()
