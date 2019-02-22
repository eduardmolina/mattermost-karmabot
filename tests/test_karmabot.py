import unittest
from unittest.mock import MagicMock

from src.karmabot import KarmaBot

class TestKarmaBot():
    def setUp(self):
        self.bot = KarmaBot(MagicMock(), MagicMock(), MagicMock())

    def test_parse_message(self):
        response = self.bot._parse_message('@cachorro_quente++')

        assert response == {
            'target': 'cachorro_quente',
            'action': 1,
        }

        response = self.bot._parse_message('@brócolis--')
        assert response == {
            'target': 'brócolis',
            'action': -1,
        }

        response = self.bot._parse_message('@pão_de_queijo+-')
        assert response == {
            'target': 'pão_de_queijo',
            'action': 0,
        }

        response = self.bot._parse_message('@anything-- something')
        assert response == {
            'target': 'anything',
            'action': -1,
        }

    def test_parse_message_empty(self):
        response = self.bot._parse_message('anything at all')

        assert response == {}
