# heare-config
Configuration library used by projects under heare.io

[![Build Status](https://app.travis-ci.com/heare-io/heare-config.svg?branch=main)](https://app.travis-ci.com/heare-io/heare-config)

# Usage
heare-config allows developers to declare typed configuration using a code-as-schema syntax.
The Setting class will infer the type of the property from the default parser.

## Basic SettingsDefinition
```python3
from heare.config import SettingsDefinition, Setting

class MyConfig(SettingsDefinition):
    foo = Setting(str)
    bar = Setting(float, default=1.0)

config: MyConfig = MyConfig.load()
```
The `MyConfig.load()` will create an instance of MyConfig with GettableConfig objects, populated accordingly.


## Default Invocation
The settings for a definition can be specified in three ways: command line flags, environment variable, and config files, with conventions matching each format to the SettingsDefinition.
By default, each setting property name is scoped by its definition class name, but will also have a short-name version for convenience, with formats relevant to the configuration source. 

### Command Line Flags
Command-line flags address config by a fully qualified flag name of the format `<class name>.<property name>`, 
a simple flag of the format `<property name>`, or a short flag of the form `<first char of property name>`.
```shell
# command line flags
$ ./main.py --foo FOO --bar 10.0

# fully qualified command line flag
$ ./main.py --MyConfig.foo FOO --MyConfig.bar 10.0

# command line short flags
$ ./main.py -f FOO -b 10.0
```

### Environment Variables
Environment variables address config by converting component names to upper snake_case, and joining parts with a double underscore `__`. 
```shell
# environment variables
$ MY_CONFIG__FOO="value" MY_CONFIG__BAR="10.0" ./main.py
$ FOO="value" BAR="10.0" ./main.py
```

### Config Files
Config files address config with sections for the config class name, and matching property value names within the sections. Config file mappings do not support any aliases.

```ini
[MyConfig]
foo = "value"
bar = 10.0
```

## Type Enforcement
Type enforcement is handled when transforming 

## Precedence
TODO

## Custom Aliases
The default aliases for each format can be optionally overloaded, to help when migrating existing applications.

## Example Definition
```python3
from heare.config import SettingsDefinition, Setting, SettingAliases

class MyAliasedConfig(SettingsDefinition):
    bar = Setting(str, aliases=SettingAliases(
        flag='BAR',
        short_flag='B',
        env_variable='NOTBAR'
    ))

config: MyAliasedConfig = MyAliasedConfig.load()
```

### Command Line Flags
```shell
$ ./main.py --MyAliasedConfig.BAR "value"
$ ./main.py --BAR "value"
$ ./main.py -B "value"
```

### Environment Variables
Environment variables address config by converting component names to upper snake_case, and joining parts with a double underscore `__`. 
```shell
$ MY_CONFIG__FOO="value" ./main.py
$ FOO="value" ./main.py

$ MY_ALIASED_CONFIG__NOTBAR="value" ./main.py
$ NOTBAR="value" ./main.py
```

## Using Multiple Configuration Classes
TODO
### Naming Collisions
TODO