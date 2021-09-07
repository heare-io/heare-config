from unittest import TestCase

from heare.config import parse_cli_arguments


class TestCLIParsing(TestCase):
    def test_parse_cli_arguments(self):
        args = [
            '--foo=bar',
            '--baz', 'bing'
        ]
        parsed, positional = parse_cli_arguments(args)

        self.assertListEqual([
            ('foo', 'bar'),
            ('baz', 'bing')
        ], parsed)

    def test_short_names(self):
        args = [
            '-f', 'bar'
        ]

        parsed, positional = parse_cli_arguments(args)

        self.assertListEqual([
            ('f', 'bar')
        ], parsed)

    def test_flags(self):
        args = [
            '--ssl',
            '--no-tls'
        ]

        parsed, positional = parse_cli_arguments(args)

        self.assertListEqual([
            ('ssl', 'TRUE'),
            ('tls', '')
        ], parsed)
