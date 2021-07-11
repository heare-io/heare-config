import os
import sys
from json import JSONEncoder
from typing import TypeVar, Generic, Callable, \
    Optional, List, Tuple, Union, Dict

T = TypeVar('T')


class SettingAliases(object):
    def __init__(self,
                 flag: Optional[str] = None,
                 short_flag: Optional[str] = None,
                 env_variable: Optional[str] = None,
                 dotted_name: Optional[str] = None):
        """
        Specify aliases for a config property
        :param flag: an alternate flag name that does not
            match the schema property name
        :param short_flag: maps short-flag name for CLI parsing
        :param env_variable: maps an environment variable
            name to the property
        :param dotted_name: maps a dotted name to a config tree
            from a parsed json/ini file
        """
        self.flag: Optional[str] = flag
        self.short_flag: Optional[str] = short_flag
        self.env_variable: Optional[str] = env_variable
        self.dotted_name: Optional[str] = dotted_name


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
        :param aliases: a {@code heare.config.ConfigPropertyAliases} object
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


#############################################
# CLI parsing functions
#############################################
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


#############################################
# Config File Parsing Functions
#############################################
def search_for_config(directory_name,
                      extensions=['.json', '.conf', '.ini']):
    for root, subdirs, files in os.walk(directory_name):
        for f in files:
            if os.path.splitext(f) in extensions:
                yield os.path.join(root, f)

def parse_ini():
    pass


##################################################################
# Sanity block
#
# We _will_ be parsing multiple sources
# Each source parser will yield a mapping informed by the schema
# The schema, per ConfigProperty, will enforce precedence from the
# set of results
##################################################################


class SettingsDefinition(object):
    @classmethod
    def load(cls, args=None, env=None, files_or_directories=None):
        args = args or sys.argv
        env = env or os.environ
        result = cls()
        setting_specs = {}
        setting_name_mapping = {}
        setting_env_mapping = {}

        intermediate_results: Dict[str, List[GettableSetting]] = dict()

        for name, value in cls.__dict__.items():
            if isinstance(value, Setting):
                setting_specs[name] = (name, value)
                setting_name_mapping[name] = name
                aliases = value.aliases
                if aliases:
                    setting_name_mapping[aliases.flag or name] = name
                    setting_name_mapping[aliases.short_flag or name] = name
                    if aliases.env_variable:
                        setting_env_mapping[aliases.env_variable] = name

        cli_args, positional = parse_cli_arguments(args)


        # use configparser to load config files (either dict or ini)
        extensions = ['.json', '.conf', '.ini']
        resolved_files = []
        for path in (files_or_directories or []):
            if not os.path.exists(path):
                continue
            if os.path.isfile(path):
                ext = os.path.splitext(path)
                if ext not in extensions:
                    continue
                resolved_files.append(path)
            elif os.path.isdir(path):
                resolved_files += list(search_for_config(path, extensions))





        # apply cli values to intermediate_results
        for name_or_flag, value in cli_args:
            resolved_name = setting_name_mapping.get(name_or_flag)
            if not resolved_name:
                # skipping unknown
                continue
            arg_name, setting_spec = setting_specs[resolved_name]
            intermediate_result_list = intermediate_results.get(arg_name, [])
            if not intermediate_result_list:
                intermediate_results[arg_name] = intermediate_result_list

            intermediate_result_list.append(
                GettableSetting(
                    value=setting_spec.from_raw_value(value),
                    formatter=setting_spec.formatter,
                    default=setting_spec.default,
                    required=setting_spec.required
                )
            )

        # apply env_variables to intermediate results
        for env_name, resolved_name in setting_env_mapping.items():
            env_value = env.get(env_name)
            if env_value is not None:
                arg_name, setting_spec = setting_specs[resolved_name]
                intermediate_result_list = intermediate_results.get(arg_name,
                                                                    [])
                if not intermediate_result_list:
                    intermediate_results[arg_name] = intermediate_result_list

                intermediate_result_list.append(
                    GettableSetting(
                        value=setting_spec.from_raw_value(env_value),
                        formatter=setting_spec.formatter,
                        default=setting_spec.default,
                        required=setting_spec.required
                    )
                )

        # apply intermediate results to a fully hydrated config object
        for name, (_, setting_spec) in setting_specs.items():
            setting_candidates = intermediate_results.get(name, [])

            if setting_spec.required and \
                    not (setting_candidates or setting_spec.default):
                raise ValueError(
                    f"Required config not satisfied: {name}, {setting_spec}"
                )

            value = setting_spec.default if \
                not setting_candidates else setting_candidates[-1].value

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
