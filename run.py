import os

from src import KarmaBot
from utils import json_to_dict


if __name__ == '__main__':
    config = json_to_dict(
        os.getenv('CONFIG_PATH', 'config/karmaconf.json'))

    mattermost_config = config['MATTERMOST']
    karma_bot = KarmaBot(
        mattermost_config['MM_ACCESS_TOKEN'],
        mattermost_config['MM_WEBSOCKET_URL'],
        mattermost_config['MM_INCOMING_WB_URL'])
    db_config = config['MONGO']
    karma_bot.wake_up(db_config)
