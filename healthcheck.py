import logging
import os

from utils import json_to_dict
from mongoengine import connect


def healthcheck(db_client):
    try:
        db_client.admin.command('ismaster')
    except Exception:
        logging.exception('Error while checking health')
        exit(1)

    exit(0)


if __name__ == "__main__":
    logging.basicConfig()
    config = json_to_dict(os.getenv('CONFIG_PATH', 'config/karmaconf.json'))
    db_config = config['MONGO']
    connection = connect(**db_config)
    healthcheck(connection)
