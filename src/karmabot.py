import json
import logging
import re
import requests

from mongoengine import connect
from queue import Queue
from time import sleep
from threading import Thread
from websocket import create_connection

from .models import Target


class KarmaBot(object):
    def __init__(self, mm_token, mm_wss_url, mm_incoming_wb, db_config):
        self.karma_pattern_re = r'@(\S*)([\+|\-]{2,}).*'
        self.mm_incoming_wb = mm_incoming_wb
        self.mm_token = mm_token
        self.mm_wss_url = mm_wss_url
        self.db_config = db_config
        self.tasks = Queue()
        self.wss = None
        self.registered_targets = []

    def get_header(self):
        return {
            'Connection': 'Upgrade',
            'Cookie': f'MMAUTHTOKEN={self.mm_token}',
            'User-Agent': (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
            ),
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-WebSocket-Version': '13',
            'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
            'Sec-WebSocket-Extensions': (
                'permessage-deflate; client_max_window_bits'),
            'Upgrade': 'websocket',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }


    def _establish_ws_handshake(self):
        header = self.get_header()
        self.wss = create_connection(self.mm_wss_url, header=header)

        return self.wss.getstatus()

    def _listen(self):
        while True:
            data = json.loads(self.wss.recv())
            if data and data['event'] == 'posted':
                self.tasks.put(data)
            sleep(0.001)  # CPU save ;D

    @staticmethod
    def register_target(name):
        target = Target(name=name, karma=0)
        success = True

        try:
            target.save()
        except Exception as e:
            success = False
            logging.error(f'Failed to register target. {e}')

        return success

    def get_target_names(self):
        return [target.name for target in self.registered_targets]

    def update_targets(self):
        self.registered_targets = Target.objects

    @staticmethod
    def update_target_karma(username, karma):
        success = True
        try:
            target = Target.objects(name=username).first()
            target.update(inc__karma=karma)
        except Exception as e:
            success = False
            logging.error(f'Failed to update karma. {e}')

        return success, target.karma + karma

    def _parse_message(self, message):
        match = re.search(self.karma_pattern_re, message, re.I)

        if match:
            karma_type = match.groups()[1]
            action = (
                1 if karma_type == '++' else
                -1 if karma_type == '--' else
                0
            )

            return {
                'target': match.groups()[0],
                'action': action
            }

        return {}

    def _parse_task(self, task):
        post_info = json.loads(task['data']['post'])
        message = post_info['message']

        return {
            'channel': task['data']['channel_name'],
            'post_info': post_info,
            'message': message,
            **self._parse_message(message),
        }

    @staticmethod
    def build_payload(channel, score, target):
        emoji = (':ok_hand:' if score == 0 else (
            ':+1:' if score > 0 else ':-1:'))
        return {
            'channel': channel,
            'icon_url': 'https://www.mattermost.org/wp-content/uploads/2016/04/icon.png',
            'text': f"** @{target}'s** Karmascore: {score} | {emoji}"
        }

    def send_score(self, payload):
        return requests.post(url=self.mm_incoming_wb, data=json.dumps(payload))

    def _process_tasks(self):
        registered_targets = self.get_target_names()
        while True:
            task = self.tasks.get()
            if task:
                parsed_task = self._parse_task(task)
                if parsed_task.get('target'):
                    if parsed_task['target'] not in registered_targets:
                        success = self.register_target(parsed_task['target'])
                        if not success:
                            continue

                        self.update_targets()
                        registered_targets = self.get_target_names()

                    success, karma = self.update_target_karma(
                        parsed_task['target'], parsed_task['action'])
                    if success:
                        payload = self.build_payload(
                            parsed_task['channel'],
                            karma,
                            parsed_task['target']
                        )
                        self.send_score(payload)

            sleep(0.001)  # CPU save ;D

    def wake_up(self):
        connect(**self.db_config)
        self.update_targets()

        wss_status = self._establish_ws_handshake()

        if wss_status == 101:
            listen_task = Thread(target=self._listen)
            listen_task.start()
            self._process_tasks()
        else:
            logging.error(
                'Failed to establish handshake. '
                'Return code {}'.format(wss_status))
