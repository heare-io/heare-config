# heare-config
Configuration library used by projects under heare.io

# Usage
heare-config allows developers to declare typed configuration using a code-as-schema syntax.
The ConfigProperty class will infer the type of the property from the default parser.

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
By default, each setting property name is scoped by its definition class name, but will also have a short-name version usable when there are collisions.

### Example Definition 
```python3
class MyConfig(SettingsDefinition):
    foo = Setting(str)
```
#### Command Line Flags
```bash
./main.py --MyConfig.foo "value"
./main.py --foo "value"
```

#### Environment Variables
```bash
MY_CONFIG__FOO="value" ./main.py
FOO="value" ./main.py
```

#### Config Files
```ini
[MyConfig]
foo = "value"
```

## Using Multiple SettingsDefinitions
TODO