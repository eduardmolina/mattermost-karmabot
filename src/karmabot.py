import json
import logging
import re

from mongoengine import connect
from queue import Queue
from time import sleep
from threading import Thread
from websocket import create_connection

from .models import User


class KarmaBot(object):

    def __init__(self, mm_token, mm_wss_url):
        self.plusplus_re = '@([a-z0-9_\-\.]+)\+{2,}'
        self.minusminus_re = '@([a-z0-9_\-\.]+)\-{2,}'
        self.mm_token = mm_token
        self.mm_wss_url = mm_wss_url
        self.tasks = Queue()
        self.wss = None
        self.registered_users = []

    def get_header(self):
        header = {
            'Connection': 'Upgrade',
            'Cookie': 'MMAUTHTOKEN={}'.format(self.mm_token),
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-WebSocket-Version': '13',
            'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
            'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
            'Upgrade': 'websocket', 'Pragma': 'no-cache',
            'Sec-WebSocket-Key': 'UKu19f//Z3v2mkKqSfw2aQ==',
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
            sleep(0.001) # CPU save ;D

    @staticmethod
    def register_user(user_id, name):
        user = User(
            user_id=user_id,
            name=name,
            karma=0)
        success = True
        try:
            user.save()
        except Exception as e:
            success = False
            logging.error(e)

        return success

    def get_registered_users_by_name(self):
        return [user.name for user in self.registered_users]

    def update_registered_users(self):
        self.registered_users = User.objects

    @staticmethod
    def update_user_karma(username, karma):
        user = User.objects.filter(name=username).first()
        success = True
        try:
            user.karma += karma
            user.save()
        except Exception as e:
            success = False
            logging.error(e)

        return success

    def _process_tasks(self):
        registered_usernames = self.get_registered_users_by_name()
        while True:
            task = self.tasks.get()
            if task:
                task_data = task['data']
                post_info = json.loads(task_data['post'])
                
                sender_name = task_data['sender_name']
                user_id = post_info['user_id']
                message = post_info['message']

                if sender_name not in registered_usernames:
                    success = self.register_user(user_id, sender_name)
                    if success:
                        self.update_registered_users()
                        registered_usernames = self.get_registered_users_by_name()
                    else:
                        logging.error('Failed to register user')
                        continue

                plus_match = re.search(self.plusplus_re, message, re.I)
                minus_match = re.search(self.minusminus_re, message, re.I)
                
                if plus_match:
                    self.update_user_karma(plus_match.groups(1)[0], 1)
                elif minus_match:
                    self.update_user_karma(minus_match.groups(1)[0], -1)

            sleep(0.001) # CPU save ;D

    def wake_up(self):
        connect('karmadb')
        self.update_registered_users()

        wss_status = self._establish_ws_handshake()

        if wss_status == 101:
            listen_task = Thread(target=self._listen)
            listen_task.start()
            self._process_tasks()
        else:
            logging.error(
                'Failed to establish handshake. ' \
                'Return code {}'.format(wss_status))
