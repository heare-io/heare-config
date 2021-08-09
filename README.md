# heare-config
Configuration library used by projects under heare.io

# Usage
heare-config allows developers to declare typed configuration using a code-as-schema syntax.
The Setting class will infer the type of the property from the default parser.

## Command line parsing
```python3
class MyConfig(SettingsDefinition):
    foo = Setting(str)
    bar = Setting(float, default=1.0)
```

When invoked from the command line...

```bash
./main.py --foo FOO --bar 10.0
```

The parser will create an instance of MyConfig with GettableConfig objects, populated accordingly.

## Using a Single SettingsDefinition
The settings for a definition can be specified in 3 ways: command line flags, environment variable, and config files, with conventions matching each format to the SettingsDefinition.
By default, each setting property name is scoped by its definition class name, but will also have a short-name version for convenience, with formats relevant to the configuration source. 

### Example Definition 
```python3
from heare.config import SettingsDefinition, Setting, SettingAliases

class MyConfig(SettingsDefinition):
    foo = Setting(str)

class MyAliasedConfig(SettingsDefinition):
    bar = Setting(str, aliases=SettingAliases(
        flag='BAR',
        short_flag='B',
        env_variable='NOTBAR'
    ))
```
#### Command Line Flags
Command-line flags address config by a fully qualified flag name of the format `<class name>.<property name>`, 
a simple flag of the format `<property name>`, or a short flag of the form `<first char of property name>`.



```bash
./main.py --MyConfig.foo "value"
./main.py --foo "value"
./main.py -f "value"

./main.py --MyAliasedConfig.BAR "value"
./main.py --BAR "value"
./main.py -B "value"
```

#### Environment Variables
Environment variables address config by converting component names to upper snake_case, and joining parts with a double underscore `__`. 
```bash
MY_CONFIG__FOO="value" ./main.py
FOO="value" ./main.py

MY_ALIASED_CONFIG__NOTBAR="value" ./main.py
NOTBAR="value" ./main.py
```

#### Config Files
Config files address config with sections for the config class name, and matching property value names within the sections. Config file mappings do not support any aliases.
```ini
[MyConfig]
foo = "value"

[MyAliasedConfig]
bar = "value"
```
