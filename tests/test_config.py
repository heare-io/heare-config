import unittest

from heare.config import ConfigDefinition, ConfigProperty


class ConfigDefinitionTests(unittest.TestCase):
    def test_load(self):
        class MyConfig(ConfigDefinition):
            foo = ConfigProperty(str)
            bar = ConfigProperty(float, 1.0)

        args = ['--foo=bar', '--bar=2.0']

        result = MyConfig.load(args)
        self.assertTrue(isinstance(result, MyConfig))
        self.assertEqual('bar', result.foo)
        self.assertEqual(2.0, result.bar)

    def test_default(self):
        class MyConfig(ConfigDefinition):
            foo = ConfigProperty(str)
            bar = ConfigProperty(float, 1.0)

        args = ['--foo=bar']

        result = MyConfig.load(args)
        self.assertTrue(isinstance(result, MyConfig))
        self.assertEqual('bar', result.foo)
        self.assertEqual(1.0, result.bar)

    def test_bad_parser(self):
        class MyConfig(ConfigDefinition):
            foo = ConfigProperty(str)
            bar = ConfigProperty(float, 1.0)

        args = ['--foo=bar', '--bar=bing']

        with self.assertRaises(ValueError):
            MyConfig.load(args)
