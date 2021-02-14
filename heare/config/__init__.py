import sys
from json import JSONEncoder
from typing import TypeVar, Generic, Callable, \
    Optional, List, Tuple, Union, Dict

T = TypeVar('T')


class ConfigPropertyAliases(object):
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
            name to the property (TODO)
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


class ConfigProperty(Generic[T]):
    def __init__(self,
                 formatter: Callable[[str], T],
                 default: Optional[T] = None,
                 required: bool = True,
                 aliases: Optional[ConfigPropertyAliases] = None):
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
        self.aliases: Optional[ConfigPropertyAliases] = aliases

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


class GettableConfig(ConfigProperty[T]):
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
# The schema, per ConfigProperty, will enforce precedence from the
# set of results
##################################################################


class ConfigDefinition(object):
    @classmethod
    def load(cls, args=None):
        args = args or sys.argv
        result = cls()
        config_prop_specs = {}
        config_spec_name_mapping = {}
        for name, value in cls.__dict__.items():
            if isinstance(value, ConfigProperty):
                config_prop_specs[name] = (name, value)
                config_spec_name_mapping[name] = name
                aliases = value.aliases
                if aliases:
                    config_spec_name_mapping[aliases.flag or name] = name
                    config_spec_name_mapping[aliases.short_flag or name] = name

        cli_args, positional = parse_cli_arguments(args)

        intermediate_results: Dict[str, List[GettableConfig]] = dict()

        for name_or_flag, value in cli_args:
            resolved_name = config_spec_name_mapping[name_or_flag]
            arg_name, prop_spec = config_prop_specs[resolved_name]
            intermediate_result_list = intermediate_results.get(arg_name, [])
            if not intermediate_result_list:
                intermediate_results[arg_name] = intermediate_result_list

            intermediate_results[arg_name].append(
                GettableConfig(
                    value=prop_spec.from_raw_value(value),
                    formatter=prop_spec.formatter,
                    default=prop_spec.default,
                    required=prop_spec.required
                )
            )

        # apply intermediate results to a fully hydrated config object
        for name, (_, prop_spec) in config_prop_specs.items():
            prop_candidates = intermediate_results.get(name, [])

            if prop_spec.required and \
                    not (prop_candidates or prop_spec.default):
                raise ValueError(
                    f"Required config not satisfied: {name}, {prop_spec}"
                )

            value = prop_spec.default if \
                not prop_candidates else prop_candidates[-1].value

            setattr(
                result,
                name, GettableConfig(
                    value=prop_spec.from_raw_value(value),
                    formatter=prop_spec.formatter,
                    default=prop_spec.default,
                    required=prop_spec.required
                )
            )

        return result
