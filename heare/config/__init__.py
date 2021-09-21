import copy
import os
import re
import sys
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from json import JSONEncoder
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
        return getattr(o, '__name__', '') \
               or getattr(o, '__dict__', '') \
               or 'unserializable'


SettingType = TypeVar('SettingType')


class Setting(Generic[T]):
    def __init__(self,
                 formatter: Callable[[str], T],
                 default: Optional[T] = None,
                 required: bool = True,
                 aliases: Optional[SettingAliases] = None):
        """
        Specify the schema for an individual configuration property.
        :param formatter: parses a string value into a parsed value of type T.
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
        serializable = self.__dict__.copy()
        serializable['__class__'] = self.__class__.__name__
        return JsonEncoder().encode(serializable)

    def get(self) -> Optional[T]:
        return self.default

    def to_gettable(self, value: List[T]):
        return GettableSetting(
            value,
            self.formatter,
            self.default,
            self.required
        )


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


class ListSetting(Generic[T]):
    def __init__(self,
                 formatter: Callable[[str], T],
                 default: Optional[List[T]] = None,
                 required: bool = True,
                 aliases: Optional[SettingAliases] = None):
        """
        Specify the schema for an individual configuration property.
        :param formatter: parses the elements of a string value into
        :param default: default value if no configuration is specified
        :param required: indicates that this property is required
        """
        self.formatter: Callable[[str], T] = formatter
        self.default: Optional[List[T]] = default
        self.required: bool = required
        self.aliases: Optional[SettingAliases] = aliases

    def from_raw_value(self, value: str) -> List[T]:
        result: List[T] = []
        # ListSetting assumes values are CSV. Repeated command line flags
        # must be treated specially, but will also work with csv values.
        value_parts = value.split(",")  # TODO: Replace with csv lib?
        for part in value_parts:
            try:
                result.append(self.formatter(part))
            except Exception as _:
                raise ValueError(
                    f"{value} cannot be parsed as {self.formatter.__name__}"
                )
        return result

    def get(self) -> Optional[List[T]]:
        return self.default

    def to_gettable(self, value: List[T]):
        return GettableListSetting(
            value,
            self.formatter,
            self.default,
            self.required
        )


class GettableListSetting(ListSetting[T]):
    def __init__(self,
                 value: Optional[List[T]],
                 formatter: Callable[[str], T],
                 default: Optional[List[T]] = None,
                 required: bool = True):
        super().__init__(
            formatter=formatter,
            default=default,
            required=required
        )
        self.value: Optional[List[T]] = value

    def get(self) -> Optional[List[T]]:
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
                                  or args[idx + 1].startswith('-')
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

    @staticmethod
    def merge(raw_name: str, raw_settings: List['RawSetting']) -> 'RawSetting':
        merged_value: str = ','.join([str(setting.raw_value)
                                      for setting in raw_settings])
        return RawSetting(raw_name, merged_value)


class SettingsSource(metaclass=ABCMeta):
    @abstractmethod
    def get_raw_setting(self,
                        namespace: Optional[str],
                        canonical_name: str,
                        aliases: Optional[SettingAliases],
                        as_list: bool = False) -> \
            Optional[RawSetting]:
        """
        :param namespace: namespace for config name_or_alias, typically maps to
            a SettingsDefinition class name
        :param canonical_name: a string name, sources from either
            SettingsDefinition property name.
        :param aliases: optional SettingAliases instance, specifies aliases
            from definition.
        :param as_list: whether to pull all existing matching values as a list.
        :return: RawSetting if found, else None
        """
        raise NotImplementedError()


class CLISettingsSource(SettingsSource):
    def __init__(self, args: List[str] = sys.argv):
        self.args = args
        self.raw_settings: Dict[str, List[RawSetting]] = defaultdict(list)
        for rs in self.load():
            self.raw_settings[rs.raw_name].append(rs)

    def load(self) -> List[RawSetting]:
        flag_arguments, positional = parse_cli_arguments(self.args)
        results: List[RawSetting] = []
        for flag_arg in flag_arguments:
            results.append(RawSetting(flag_arg[0], flag_arg[1]))

        return results

    def get_raw_setting(self,
                        namespace: Optional[str],
                        canonical_name: str,
                        aliases: Optional[SettingAliases],
                        as_list: bool = False) -> \
            Optional[RawSetting]:
        """
        :param namespace: namespace for config name_or_alias, typically maps to
            a SettingsDefinition class name
        :param canonical_name: a string name, sources from either
            SettingsDefinition property name.
        :param aliases: options SettingAliases instance, specifies aliases from
            definition.
        :param as_list: whether to pull all existing matching values as a list.
        :return: RawSetting if found, else None
        """
        intermediate_results: List[RawSetting] = []

        local_name = canonical_name

        if aliases and aliases.flag:
            local_name = aliases.flag

        short_flag = local_name[0]
        if aliases and aliases.short_flag:
            short_flag = aliases.short_flag

        forms = [
            local_name,  # property name
            short_flag,  # short flag
        ]

        if namespace:
            forms = [
                        f"{namespace}.{local_name}",  # fully qualified form
                    ] + forms

        for form in forms:
            candidates = self.raw_settings.get(form)
            if as_list and candidates is not None:
                intermediate_results.append(RawSetting.merge(form, candidates))
            elif candidates and len(candidates) > 0:
                intermediate_results.append(candidates[-1])

        if intermediate_results and len(intermediate_results) > 1:
            raise ValueError(f"Multiple forms of {forms[0]} used in CLI "
                             f"arguments, an illegal combination.")
        return intermediate_results[0] if intermediate_results else None


def camel_to_big_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).upper()


FlexibleEnvironType = Union[os._Environ, Dict[str, str]]


class EnvironSettingsSource(SettingsSource):
    def __init__(self, environ: FlexibleEnvironType):
        self.raw_settings = copy.copy(environ)

    def get_raw_setting(self,
                        namespace: Optional[str],
                        canonical_name: str,
                        aliases: Optional[SettingAliases],
                        as_list: bool = False) -> \
            Optional[RawSetting]:
        """
        :param namespace: namespace for config name_or_alias, typically maps to
            a SettingsDefinition class name
        :param canonical_name: a string name, sources from either
            SettingsDefinition property name.
        :param aliases: options SettingAliases instance, specifies aliases from
            definition.
        :param as_list: whether to pull all existing matching values as a list.
        :return: RawSetting if found, else None
        """
        local_name = canonical_name
        if aliases and aliases.env_variable:
            local_name = aliases.env_variable
        formatted_name = camel_to_big_snake(local_name)

        forms = []

        # fully qualified name
        if namespace:
            formatted_namespace = camel_to_big_snake(namespace)
            full_name = f"{formatted_namespace}__{formatted_name}"
            if full_name in self.raw_settings:
                forms.append(RawSetting(
                    full_name, self.raw_settings[full_name]))

        # check for short name
        if formatted_name in self.raw_settings:
            forms.append(RawSetting(
                formatted_name,
                self.raw_settings[formatted_name]))
        if len(forms) == 1:
            return forms[0]
        elif len(forms) > 1:
            raise ValueError(f"Multiple forms of {forms[0]} in environment "
                             f"variables, an illegal combination.")
        else:
            return None


class ConfigFileSource(SettingsSource):
    @staticmethod
    def from_filename(filename: str) -> 'ConfigFileSource':
        config_parser = configparser.ConfigParser()
        config_parser.read(filename)
        return ConfigFileSource(config_parser)

    @staticmethod
    def from_string(content: str) -> 'ConfigFileSource':
        config_parser = configparser.ConfigParser()
        config_parser.read_string(content)
        return ConfigFileSource(config_parser)

    def __init__(self, config_parser: configparser.ConfigParser):
        self.config_parser = config_parser

    def get_raw_setting(self,
                        namespace: Optional[str],
                        canonical_name: str,
                        aliases: Optional[SettingAliases],
                        as_list: bool = False) -> \
            Optional[RawSetting]:
        """
        :param namespace: namespace for config name_or_alias, typically maps to
            a SettingsDefinition class name
        :param canonical_name: a string name, sources from either
            SettingsDefinition property name.
        :param aliases: options SettingAliases instance, specifies aliases from
            definition. Ignored in this implementation.
        :param as_list: whether to pull all existing matching values as a list.
        :return: RawSetting if found, else None
        """
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
            if not (isinstance(value, Setting)
                    or isinstance(value, ListSetting)):
                continue

            setting_specs[name] = (name, value)
            intermediate_results[name] = []

            for source in settings_sources:
                raw_setting: Optional[RawSetting] = source.get_raw_setting(
                    settings_class.__name__, name, value.aliases,
                    as_list=isinstance(value, ListSetting))

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
                name, setting_spec.to_gettable(
                    setting_spec.from_raw_value(value)
                )
            )

        return result
