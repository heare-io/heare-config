import json
import sys


class ConfigProperty(object):
    def __init__(self, formatter=str, default=None, required=True):
        self.formatter = formatter
        self.default = default
        self.required = required

    def from_raw_value(self, value: str):
        try:
            return self.formatter(value)
        except Exception as e:
            raise ValueError(
                f"{value} cannot be parsed as {self.formatter.__name__}"
            )

    def __str__(self):
        return json.dumps(self.__dict__)


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

                if arg_name in config_props:
                    setattr(
                        result,
                        arg_name,
                        config_props[arg_name].from_raw_value(arg_value)
                    )
                    del config_props[arg_name]

        for name, prop in config_props.items():
            if prop.required and not prop.default:
                raise ValueError(
                    f"Required config property not satisfied: {name}, {prop}"
                )

            setattr(result, name, prop.default)

        return result
