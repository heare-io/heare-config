import json
import sys
from typing import TypeVar, Generic, Callable, Optional

T = TypeVar('T')


class ConfigProperty(Generic[T]):
    def __init__(self,
                 formatter: Callable[[str], T],
                 default: Optional[T] = None,
                 required: bool = True):
        self.formatter: Callable[[str], T] = formatter
        self.default: Optional[T] = default
        self.required: bool = required

    def from_raw_value(self, value: str) -> T:
        try:
            return self.formatter(value)
        except Exception as _:
            raise ValueError(
                f"{value} cannot be parsed as {self.formatter.__name__}"
            )

    def __str__(self):
        return json.dumps(self.__dict__)

    def get(self) -> Optional[T]:
        raise NotImplementedError(
            "ConfigProperty.get is not implemented, intentionally."
        )


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


class ConfigDefinition(object):
    @classmethod
    def load(cls, args=None):
        args = args or sys.argv
        result = cls()
        config_props = {}
        for name, value in cls.__dict__.items():
            if isinstance(value, ConfigProperty):
                config_props[name] = value

        for arg in args:
            parts = arg.split("=")
            if len(parts) == 2 and parts[0].startswith('--'):
                arg_name = parts[0][2:]
                arg_value = parts[1]
                prop = config_props[arg_name]
                if arg_name in config_props:
                    setattr(
                        result,
                        arg_name,
                        GettableConfig(
                            value=prop.from_raw_value(arg_value),
                            formatter=prop.formatter,
                            default=prop.default,
                            required=prop.required
                        )
                    )
                    del config_props[arg_name]

        for name, prop in config_props.items():
            if prop.required and not prop.default:
                raise ValueError(
                    f"Required config property not satisfied: {name}, {prop}"
                )

            setattr(
                result,
                name, GettableConfig(
                    value=prop.default,
                    formatter=prop.formatter,
                    default=prop.default,
                    required=prop.required
                )
            )

        return result
