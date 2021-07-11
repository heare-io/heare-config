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

