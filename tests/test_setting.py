import unittest

from heare.config import SettingsDefinition, \
    Setting, SettingAliases


class SettingsDefinitionTests(unittest.TestCase):
    def test_load(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str)
            bar = Setting(float, 1.0)

        args = ['--foo=bar', '--bar=2.0']

        result = MySettings.load(args)
        self.assertTrue(isinstance(result, MySettings))
        self.assertEqual('bar', result.foo.get())
        self.assertEqual(2.0, result.bar.get())

    def test_default(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str)
            bar = Setting(float, 1.0)
            baz = Setting(bool, default=False)

        args = ['--foo=bar', '--baz']

        result = MySettings.load(args)
        self.assertTrue(isinstance(result, MySettings))
        self.assertEqual('bar', result.foo.get())
        self.assertEqual(1.0, result.bar.get())
        self.assertTrue(result.baz.get())

    def test_bad_parser(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str)
            bar = Setting(float, 1.0)

        args = ['--foo=bar', '--bar=bing']

        with self.assertRaises(ValueError):
            MySettings.load(args)

    def test_unkown_flags_ignored(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str)

        args = ['--foo=bar', '--bar=2.0']

        result = MySettings.load(args)
        self.assertTrue(isinstance(result, MySettings))
        self.assertEqual('bar', result.foo.get())

    def test_config_aliases(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str,
                          aliases=SettingAliases(short_flag='f'))
            bar = Setting(bool,
                          aliases=SettingAliases(short_flag='b'))

        args = [
            '-f', 'bar',
            '-b'
        ]

        result = MySettings.load(args)

        self.assertTrue(result.bar.get())
        self.assertEqual('bar', result.foo.get())

    def test_env_variables(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str,
                          aliases=SettingAliases(env_variable='FOO'))
            bar = Setting(bool,
                          aliases=SettingAliases(env_variable='BAR'))

        result = MySettings.load(args=[], env={'FOO': 'bar', 'BAR': 'TRUE'})

        self.assertTrue(result.bar.get())
        self.assertEqual('bar', result.foo.get())

    def test_env_variable_precedence(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str,
                          aliases=SettingAliases(
                              short_flag='f',
                              env_variable='FOO'))
            bar = Setting(bool,
                          aliases=SettingAliases(
                              short_flag='b',
                              env_variable='BAR'))

        args = [
            '-f', 'bar',
            '-b'
        ]

        result = MySettings.load(args=args, env={'FOO': 'bar', 'BAR': ''})

        self.assertFalse(result.bar.get())
        self.assertEqual('bar', result.foo.get())

    def test_config_file(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str,
                          aliases=SettingAliases(
                              dotted_name="default.foo"
                          ))
        results = MySettings.load(files_or_directories=
                                  ['tmp.conf'])

class SettingTypingTests(unittest.TestCase):
    def test_typing(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str)
            bar = Setting(float, 1.0)

        args = ['--foo=bar']

        result = MySettings.load(args)
        self.assertTrue(isinstance(result, MySettings))
        # We're extracting a local variable with type hints here
        # so that mypy has something to tell us whether or not the
        # the type hinting is correct
        foo: str = result.foo.get()
        bar: float = result.bar.get()
        self.assertEqual('bar', foo)
        self.assertEqual(1.0, bar)
