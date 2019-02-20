import os

from src import KarmaBot
from utils import json_to_dict


if __name__ == '__main__':

    config = json_to_dict(
        os.getenv('CONFIG_PATH', 'config/karmaconf.json'))

    karma_bot = KarmaBot(
        config['MM_ACCESS_TOKEN'],
        config['MM_WEBSOCKET_URL'],
        config['MM_INCOMING_WB_URL'])
    karma_bot.wake_up()
