import unittest
import tempfile

from heare.config import SettingsDefinition, \
    Setting, SettingAliases, ListSetting


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

    def test_convoluted_cli(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str)

        args = [
            '--foo=bar',
            '-f=2.0',
            '--MySettings.foo=1,2,3']

        with self.assertRaises(ValueError):
            MySettings.load(args)

    def test_convoluted_env(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str)

        env = {
            'MySettings.foo': 'foo',
            'foo': 'bar'
        }

        with self.assertRaises(ValueError):
            MySettings.load(env=env)

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

    def test_config_file_parser(self):
        class MySettings(SettingsDefinition):
            foo = Setting(str,
                          aliases=SettingAliases(
                              short_flag='f',
                              env_variable='FOO'))
            bar = Setting(float,
                          aliases=SettingAliases(
                              short_flag='b',
                              env_variable='BAR'))

        with tempfile.NamedTemporaryFile() as config_file:
            config_file.write(b"""
            [MySettings]
            foo = bar
            bar = 1.0
            """)

            config_file.flush()

            result = MySettings.load(config_files=[config_file.name])

            self.assertEqual(result.foo.get(), "bar")
            self.assertEqual(result.bar.get(), 1.0)


class ListSettingTests(unittest.TestCase):
    def test_load(self):
        class MySettings(SettingsDefinition):
            foo = ListSetting(str)
            bar = ListSetting(float, 1.0)
            baz = ListSetting(int)
            bing = ListSetting(float)

        args = [
            '--foo=bar',  # as string list with single el
            '--bar=2.0',  # as float list with single el
            '--baz=1,2,3',  # as int list with 3 el (csv)
            '--bing=1.0',  # as float list with 2 el
            '--bing=2.0']

        result = MySettings.load(args)
        self.assertTrue(isinstance(result, MySettings))
        self.assertEqual(['bar'], result.foo.get())
        self.assertEqual([2.0], result.bar.get())
        self.assertEqual([1, 2, 3], result.baz.get())
        self.assertEqual([1.0, 2.0], result.bing.get())

    def test_convoluted_cli(self):
        class MySettings(SettingsDefinition):
            foo = ListSetting(str)

        args = [
            '--foo=bar',
            '-f=2.0',
            '--MySettings.foo=1,2,3']

        with self.assertRaises(ValueError):
            MySettings.load(args)

    def test_config_file_parser(self):
        class MySettings(SettingsDefinition):
            foo = ListSetting(str,
                              aliases=SettingAliases(
                                  short_flag='f',
                                  env_variable='FOO'))
            bar = ListSetting(float,
                              aliases=SettingAliases(
                                  short_flag='b',
                                  env_variable='BAR'))

        with tempfile.NamedTemporaryFile() as config_file:
            config_file.write(b"""
            [MySettings]
            foo = bar,baz,bing
            bar = 1.0,2.0
            """)

            config_file.flush()

            result = MySettings.load(config_files=[config_file.name])

            self.assertEqual(result.foo.get(), ["bar", "baz", "bing"])
            self.assertEqual(result.bar.get(), [1.0, 2.0])


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
