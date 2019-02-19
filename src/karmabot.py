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

    def __init__(self, mm_token, mm_wss_url, mm_incoming_wb):
        self.plusplus_re = '@([a-z0-9_\-\.]+)\+{2,}'
        self.minusminus_re = '@([a-z0-9_\-\.]+)\-{2,}'
        self.mm_incoming_wb = mm_incoming_wb
        self.mm_token = mm_token
        self.mm_wss_url = mm_wss_url
        self.tasks = Queue()
        self.wss = None
        self.registered_targets = []

    def get_header(self):
        header = {
            'Connection': 'Upgrade',
            'Cookie': 'MMAUTHTOKEN={}'.format(self.mm_token),
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-WebSocket-Version': '13',
            'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
            'Sec-WebSocket-Extensions': 'permessage-deflate; '
            'client_max_window_bits',
            'Upgrade': 'websocket', 'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

        return header

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
        target = Target(
            name=name,
            karma=0)
        success = True
        try:
            target.save()
        except Exception as e:
            success = False
            logging.error(e)

        return success

    def get_target_names(self):
        return [target.name for target in self.registered_targets]

    def update_targets(self):
        self.registered_targets = Target.objects

    @staticmethod
    def update_target_karma(username, karma):
        target = Target.objects.filter(name=username).first()
        success = True
        try:
            target.karma += karma
            target.save()
        except Exception as e:
            success = False
            logging.error(e)

        return success, target.karma

    def _parse_task(self, task):
        parsed_task = {}
        parsed_task['channel'] = task['data']['channel_name']
        parsed_task['post_info'] = json.loads(task['data']['post'])
        parsed_task['message'] = parsed_task['post_info']['message']

        plus_match = re.search(
            self.plusplus_re, parsed_task['message'], re.I)
        minus_match = re.search(
            self.minusminus_re, parsed_task['message'], re.I)

        if plus_match:
            parsed_task['target'] = plus_match.groups(1)[0]
            parsed_task['action'] = 1
        elif minus_match:
            parsed_task['target'] = minus_match.groups(1)[0]
            parsed_task['action'] = -1

        return parsed_task

    @staticmethod
    def build_payload(channel, score, target):
        payload = {
            'channel': channel,
            'icon_url': 'https://www.mattermost.org/wp-content/uploads/2016/04/icon.png',
            'text': "#### | {}'s Karmascore: {} | {}".format(
                target, score, ':+1:' if score >= 0 else ':-1:')
        }

        return payload

    def send_score(self, payload):
        response = requests.post(
            url=self.mm_incoming_wb,
            data=json.dumps(payload))

        return response

    def _process_tasks(self):
        registered_targets = self.get_target_names()
        while True:
            task = self.tasks.get()
            if task:
                parsed_task = self._parse_task(task)
                if parsed_task.get('target'):
                    if parsed_task['target'] not in registered_targets:
                        success = self.register_target(parsed_task['target'])
                        if success:
                            self.update_targets()
                            registered_targets = \
                                self.get_target_names()
                        else:
                            logging.error('Failed to register target')
                            continue

                    s, karma = self.update_target_karma(
                        parsed_task['target'], parsed_task['action'])
                    if s:
                        payload = self.build_payload(
                            parsed_task['channel'],
                            karma,
                            parsed_task['target'])
                        self.send_score(payload)
                    else:
                        logging.error('Failed to update karma')

            sleep(0.001)  # CPU save ;D

    def wake_up(self):
        connect(host='localhost', db='karmadb')
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
