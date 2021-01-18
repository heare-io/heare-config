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
        self.assertEqual('bar', result.foo.get())
        self.assertEqual(2.0, result.bar.get())

    def test_default(self):
        class MyConfig(ConfigDefinition):
            foo = ConfigProperty(str)
            bar = ConfigProperty(float, 1.0)

        args = ['--foo=bar']

        result = MyConfig.load(args)
        self.assertTrue(isinstance(result, MyConfig))
        self.assertEqual('bar', result.foo.get())
        self.assertEqual(1.0, result.bar.get())

    def test_bad_parser(self):
        class MyConfig(ConfigDefinition):
            foo = ConfigProperty(str)
            bar = ConfigProperty(float, 1.0)

        args = ['--foo=bar', '--bar=bing']

        with self.assertRaises(ValueError):
            MyConfig.load(args)


class ConfigTypingTests(unittest.TestCase):
    def test_typing(self):
        class MyConfig(ConfigDefinition):
            foo = ConfigProperty(str)
            bar = ConfigProperty(float, 1.0)

        args = ['--foo=bar']

        result = MyConfig.load(args)
        self.assertTrue(isinstance(result, MyConfig))
        # We're extracting a local variable with type hints here
        # so that mypy has something to tell us whether or not the
        # the type hinting is correct
        foo: str = result.foo.get()
        bar: float = result.bar.get()
        self.assertEqual('bar', foo)
        self.assertEqual(1.0, bar)
