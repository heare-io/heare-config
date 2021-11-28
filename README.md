# heare-config
Configuration library used by projects under heare.io


# Usage
heare-config allows developers to declare typed configuration using a code-as-schema syntax.
The Setting class will infer the type of the property from the default parser.

## Basic SettingsDefinition
```python3
from heare.config import SettingsDefinition, Setting

class MyConfig(SettingsDefinition):
    foo = Setting(str, default="bazinga")
    bar = Setting(float, default=1.0)

config: MyConfig = MyConfig.load()
config.foo.get()  # "bazinga"
config.bar.get()  # 1.0
```
The `MyConfig.load()` will create an instance of MyConfig with GettableConfig objects, populated accordingly.

### ListSettings
The `ListSetting` is a version of `Setting` that yields results as a list. Usage varies slightly between command line, environment variables, and config files.
```python3
from heare.config import SettingsDefinition, ListSetting, SettingAliases

class MyListConfig(SettingsDefinition):
    numbers = ListSetting(int, default=[], aliases=SettingAliases(
        flag='number'
    ))

config: MyListConfig = MyListConfig.load()
config.numbers.get()  # []
```

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

#### Multiple Values with ListSettings
Command-line flags can be specified multiple times. With a standard setting, the last specified flag will override any previous values. With a ListSetting, a list will be created
with order matching the command line invocation.
```shell
$ ./main.py --number 1 --number 2

# fully qualified command line flag
$ ./main.py --MyListConfig.number 1 --MyListConfig.number 2

# command line short flags
$ ./main.py -f FOO -b 10.0
```
*Note:* It is invalid to mix formats of command line flags in a single invocation. The following example will yield a runtime error.
```shell
$ ./main.py --MyListConfig.number 1 --number 2  # foo == [1, 2]
```

*Note:* As the parsers share a common utility class, it is technically possible to merge multiple ListSettings together by use of multiple csv values for a flag. 
This is not considered a best practice, and may be deprecated in a future refactoring.
```shell
$ ./main.py --number 1,2,3 --number 4,5,6  # foo = [1,2,3,4,5,6]
```

### Environment Variables
Environment variables address config by converting component names to upper snake_case, and joining parts with a double underscore `__`. 
```shell
# environment variables
$ MY_CONFIG__FOO="value" MY_CONFIG__BAR="10.0" ./main.py
$ FOO="value" BAR="10.0" ./main.py
```
*Note:* At this time, quotations and other escape characters are not supported.

#### Multiple Values with ListSettings
Environment Variables allow for multiple values to be specified for a single property using comma-separated values. 


```shell
# environment variables
$ MY_LIST_CONFIG__NUMBERS="1,2,3" ./main.py
$ NUMBERS="1,2,3" ./main.py
```
*Note:* At this time, quotations and other escape characters are not supported.

*Note:* It is invalid to mix formats of environment variables in a single invocation. Values will be set based on [`precedence`](#Precedence).

### Config Files
Config files address config with sections for the config class name, and matching property value names within the sections. Config file mappings do not support any aliases.

```ini
[MyConfig]
foo = "value"
bar = 10.0
```

#### Multiple Values with ListSettings
Config Files allow for multiple values to be specified for a single property using comma-separated values. 

*Note:* At this time, quotations and other escape characters are not supported.

#### Collisions across Multiple Configuration Files
When multiple configuration files are specified and the files contain colliding section/properties, values will match the last specified file.

## Type Enforcement
Type enforcement is handled when transforming 

## <a name="Precedence"></a>Precedence
If a configuration value is specified in multiple ways, the value in SettingsDefinition classes will be determined by precedence.
There are two layers of precedence: precedence of settings sources (CLI, Environment, and Config Files), and within a settings source (when a property can be set multiple times).

### Precedence of Settings Sources
The loader will check each settings source in the following order, and stop when first discovered.
1. CLI Arguments
2. Environment Variables
3. Config Files
4. Default from Setting

### Precedence Within Settings Sources
Different settings sources will behave differently, and again differently based on the type of `Setting` being used (singleton vs list).

#### Command Line Arguments for Settings and ListSettings
A `Setting` specified via the CLI will take the last value specified at the command line.
```shell
$ ./main.py --foo bar --foo baz  # MyConfig.foo == "baz" 
```

A `ListSetting` specified via the CLI will collect values specified at the command line, with the notable exception that mixed formats are 
[not allowed](#Collisions).

#### Environment Variables for Settings and ListSettings
Environment variables cannot contain multiple values within a single shell session. The most recent assignment of the variable specifies the value.
It is considered invalid to specify multiple forms of the same environment variable, as it is potentially ambiguous. 

```shell
$ FOO="bar" MY_CONFIG__FOO="baz" ./main.py  # Raises an error, for both Setting and ListSetting
```

#### Config Files for Settings and ListSettings
Config files will be merged in the order specified. When section collisions occur, the values from the last file will override individual properties within the section.
```ini
# file1.ini
[MyConfig]
foo = bar
bar = 1.0

# file2.ini
[MyConfig]
bar = 2.0

# MyConfig.foo == bar
# MyConfig.bar == 2.0
```

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

## Using Multiple SettingsDefinitions
It's possible to declare multiple `SettingsDefinitions` classes within a program. `SettingsDefinition.load()` can be invoked on multiple classes, 
and SettingsDefinition provides a convenience mechanism for discovering all `SettingsDefinitions`.
```python
from typing import Dict
from heare.config import SettingsDefinition

all_settings:Dict[type, SettingsDefinition] = {
    definition: definition.load() for definition in SettingsDefinition.discover()
}
```

### <a name="Collisions"></a>Naming Collisions with Multiple SettingsDefinitions
Property reuse is encouraged, but ambiguity is discouraged. As noted above, it is illegal to specify multiple formats of a Setting in a single invocation.
Across settings sources, precedence handles this cleanly, however within a single source there is the potential for ambiguity.

The following example demonstrates two conflicting and potentially ambiguous configurations.

```python
from heare.config import SettingsDefinition, Setting, ListSetting

class MyFirstConfig(SettingsDefinition):
    foo = ListSetting(str)

class MySecondConfig(SettingsDefinition):
    foo = Setting(str)
```
```shell
$ ./main.py --MyFirstConfig.foo=bar --foo=baz
```

In the above scenario, it's not clear whether the `--foo` setting should be a member of `MyFirstConfig.foo` or not. While this will more clearly fail
when `MyFirstConfig.foo` and `MySecondConfig.foo` are of different types, the ambiguity here allows for unexpected surprises. Instead, only unambiguous 
invocations are allowed: where sharing is implicit and consistent, or distinct values are explicit.

```shell
$ ./main.py --foo=bar  # valid!

# MyFirstConfig.foo = ["bar"]
# MySecondConfig.foo = "bar"

$ ./main.py --MyFirstConfig.foo=bar --MySecondConfig.foo=baz  # valid!
# MyFirstConfig.foo = ["bar"]
# MySecondConfig.foo = "baz"
```




