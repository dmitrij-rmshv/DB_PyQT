import unittest
from argparse import ArgumentParser
from sys import argv

from chat_server import create_parser


class TestParserCreation(unittest.TestCase):

    def test_create_parser(self):
        self.assertEqual(type(create_parser()), ArgumentParser)

    def test_get_salary_fio(self):
        self.assertEqual(str(create_parser().parse_args(argv[1:])), "Namespace(address='', port=7777)")


unittest.main()
