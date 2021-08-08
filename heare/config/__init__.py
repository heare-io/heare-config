import copy
import os
import re
import sys
from abc import ABCMeta, abstractmethod
from json import JSONEncoder
from os import _Environ
from typing import TypeVar, Generic, Callable, \
    Optional, List, Tuple, Union, Dict, Generator, Set
import configparser

T = TypeVar('T')


class SettingAliases(object):
    def __init__(self,
                 flag: Optional[str] = None,
                 short_flag: Optional[str] = None,
                 env_variable: Optional[str] = None):
        """
        Specify aliases for a config property
        :param flag: an alternate flag name that does not
            match the schema property name
        :param short_flag: maps short-flag name for CLI parsing
        :param env_variable: maps an environment variable
            name to the property
        """
        self.flag: Optional[str] = flag
        self.short_flag: Optional[str] = short_flag
        self.env_variable: Optional[str] = env_variable

    def labels(self) -> List[str]:
        return list(filter(None,
                           [self.flag, self.short_flag, self.env_variable]))


class JsonEncoder(JSONEncoder):
    def default(self, o):
        return getattr(o, '__name__', '')\
               or getattr(o, '__dict__', '') \
               or 'unserializable'


class Setting(Generic[T]):
    def __init__(self,
                 formatter: Callable[[str], T],
                 default: Optional[T] = None,
                 required: bool = True,
                 aliases: Optional[SettingAliases] = None):
        """
        Specify the schema for an individual configuration property.
        :param formatter: parses a string value into
        :param default: default value if no configuration is specified
        :param required: indicates that this property is required
        """
        self.formatter: Callable[[str], T] = formatter
        self.default: Optional[T] = default
        self.required: bool = required
        self.aliases: Optional[SettingAliases] = aliases

    def from_raw_value(self, value: str) -> T:
        try:
            return self.formatter(value)
        except Exception as _:
            raise ValueError(
                f"{value} cannot be parsed as {self.formatter.__name__}"
            )

    def __str__(self):
        return JsonEncoder().encode(self.__dict__)

    def get(self) -> Optional[T]:
        return self.default


class GettableSetting(Setting[T]):
    def __init__(self,
                 value: Optional[T],
                 formatter: Callable[[str], T],
                 default: Optional[T] = None,
                 required: bool = True):
        super().__init__(
            formatter=formatter,
            default=default,
            required=required
        )
        self.value: Optional[T] = value

    def get(self) -> Optional[T]:
        return self.value


CliArgTuple = Tuple[str, Union[str, bool]]


def parse_cli_arguments(args: List[str]) -> \
        Tuple[List[CliArgTuple], List[str]]:
    idx = 0
    results: List[CliArgTuple] = []
    positional: List[str] = []
    while idx < len(args):
        cur = args[idx]
        if cur.startswith('-'):
            parts = cur.split('=')
            flag = parts[0].lstrip('-')
            if len(parts) == 1:
                is_boolean_flag = (idx == len(args) - 1) \
                                  or args[idx+1].startswith('-')
                if is_boolean_flag:
                    value = "" if flag.startswith('no-') else "TRUE"
                    if not value:
                        flag = flag[3:]
                else:
                    # flag with argument, separated by space
                    value = args[idx + 1].strip()
                    idx += 1
            else:
                value = parts[1].strip()
            results.append((flag, value))
        idx += 1

    return results, positional


##################################################################
# Sanity block
#
# We _will_ be parsing multiple sources
# Each source parser will yield a mapping informed by the schema
# The schema, per Setting, will enforce precedence from the
# set of results
##################################################################

class RawSetting(object):
    def __init__(self, raw_name: str, raw_value: Union[str, bool]):
        self.raw_name: str = raw_name
        self.raw_value: Union[str, bool] = raw_value


class SettingsSource(metaclass=ABCMeta):
    @abstractmethod
    def get_raw_setting(self,
                        namespace: Optional[str],
                        canonical_name: str) -> Optional[RawSetting]:
        raise NotImplementedError()


class CLISettingsSource(SettingsSource):
    def __init__(self, args: List[str] = sys.argv):
        self.args = args
        self.raw_settings = {rs.raw_name: rs for rs in self.load()}

    def load(self) -> List[RawSetting]:
        flag_arguments, positional = parse_cli_arguments(self.args)
        results: List[RawSetting] = []
        for flag_arg in flag_arguments:
            results.append(RawSetting(flag_arg[0], flag_arg[1]))

        return results

    def get_raw_setting(self,
                        namespace: Optional[str],
                        name_or_alias: str) -> Optional[RawSetting]:
        """

        :param namespace: namespace for config name_or_alias, typically maps to
            a SettingsDefinition class name
        :param name_or_alias: a string name or alias, soruces from either
            SettingsDefinition property name, or a defined alias.
        :return: RawSetting if found, else None
        """
        result: Optional[RawSetting] = None

        if namespace:
            canonical_form = f"{namespace}.{name_or_alias}"
            result = self.raw_settings.get(canonical_form)

        if not result:
            # prop name only
            result = self.raw_settings.get(name_or_alias)

        if not result:
            # flag
            result = self.raw_settings.get(name_or_alias[0])

        return result


def camel_to_big_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).upper()


FlexibleEnvironType = Union[_Environ, Dict[str, str]]


class EnvironSettingsSource(SettingsSource):
    def __init__(self, environ: FlexibleEnvironType):
        self.raw_settings = copy.copy(environ)

    def get_raw_setting(self,
                        namespace: Optional[str],
                        name_or_alias: str) -> Optional[RawSetting]:
        result: Optional[RawSetting] = None
        formatted_name_or_alias = camel_to_big_snake(name_or_alias)

        # fully qualified name
        if namespace:
            formatted_namespace = camel_to_big_snake(namespace)
            full_name = f"{formatted_namespace}__{formatted_name_or_alias}"
            if full_name in self.raw_settings:
                result = RawSetting(full_name, self.raw_settings[full_name])

        # check for short name
        if formatted_name_or_alias in self.raw_settings:
            result = RawSetting(
                formatted_name_or_alias,
                self.raw_settings[formatted_name_or_alias])

        return result


class ConfigFileSource(SettingsSource):
    @staticmethod
    def from_filename(filename: str) -> 'ConfigFileSource':
        config_parser = configparser.ConfigParser()
        config_parser.read(filename)
        return ConfigFileSource(config_parser)

    def from_string(self, content: str) -> 'ConfigFileSource':
        config_parser = configparser.ConfigParser()
        config_parser.read_string(content)
        return ConfigFileSource(config_parser)

    def __init__(self, config_parser: configparser.ConfigParser):
        self.config_parser = config_parser

    def get_raw_setting(self,
                        namespace: Optional[str],
                        canonical_name: str) -> Optional[RawSetting]:
        if namespace is None:
            return None

        value: Optional[str] = \
            self.config_parser.get(namespace, canonical_name, fallback=None)
        if value is None:
            return None
        else:
            return RawSetting(canonical_name, value)


class SettingsDefinition(object):
    @staticmethod
    def discover() -> Set[type]:
        subclasses: Set[type] = set()
        work = [SettingsDefinition]
        while work:
            parent = work.pop()
            for child in parent.__subclasses__():
                if child not in subclasses:
                    subclasses.add(child)
                    work.append(child)
        return subclasses

    @classmethod
    def load(cls,
             args: List[str] = sys.argv,
             env: FlexibleEnvironType = os.environ,
             config_files: List[str] = []):
        sources: List[SettingsSource] = []

        for file in config_files:
            if os.path.exists(file):
                sources.append(ConfigFileSource.from_filename(file))
        if env:
            sources.append(EnvironSettingsSource(env))
        if args:
            sources.append(CLISettingsSource(args))

        return SettingsDefinition.load_for_class(cls, sources)

    @classmethod
    def load_for_class(cls, settings_class,
                       settings_sources: List[SettingsSource]):
        result = settings_class()
        setting_specs = {}
        intermediate_results: Dict[str, List[RawSetting]] = dict()

        for name, value in settings_class.__dict__.items():
            if isinstance(value, Setting):
                setting_specs[name] = (name, value)

        for name, value in settings_class.__dict__.items():
            if not isinstance(value, Setting):
                continue
            intermediate_results[name] = []

            raw_setting: Optional[RawSetting] = None
            for source in settings_sources:
                aliases = value.aliases.labels() if value.aliases else []
                # try aliases first if specified
                for alias in aliases:
                    raw_setting = source.get_raw_setting(
                        settings_class.__name__, alias)
                    if raw_setting:
                        break

                if not raw_setting:
                    raw_setting = source.get_raw_setting(
                        settings_class.__name__, name)

                if raw_setting:
                    intermediate_results[name].append(raw_setting)

        # apply intermediate results to a fully hydrated config object
        for name, (_, setting_spec) in setting_specs.items():
            setting_candidates = intermediate_results.get(name, [])

            if setting_spec.required and \
                    not (setting_candidates or setting_spec.default):
                raise ValueError(
                    f"Required config not satisfied: {name}, {setting_spec}"
                )

            value = setting_spec.default if \
                not setting_candidates else setting_candidates[0].raw_value

            setattr(
                result,
                name, GettableSetting(
                    value=setting_spec.from_raw_value(value),
                    formatter=setting_spec.formatter,
                    default=setting_spec.default,
                    required=setting_spec.required
                )
            )

        return result
