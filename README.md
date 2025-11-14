# plain-config

Simple human-readable configuration files with automatic type conversion

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)

## Overview

`plain-config` provides a simple, human-readable configuration file format with automatic type detection and conversion. Configuration files use an intuitive `key=value` syntax with optional type modifiers, making them easy to read and edit by hand while preserving Python's rich type system.

## Features

- **Human-readable format**: Plain text `key=value` syntax anyone can edit
- **Automatic type conversion**: Integers, floats, booleans, strings, bytes, and complex objects
- **Structure preservation**: Comments, empty lines, and key ordering maintained
- **Security**: Files created with restrictive 0o600 permissions
- **No dependencies**: Pure Python using only standard library
- **Type-safe**: Automatic encoding/decoding prevents data corruption
- **Flexible**: Works with file paths, Path objects, or file-like objects

## Installation

### Via pip (from PyPI)

```bash
pip install plain-config
```

### Via pip (from git)

```bash
pip install git+https://github.com/mennucc/plain-config.git
```

### From source

```bash
git clone https://github.com/mennucc/plain-config.git
cd plain-config
pip install -e .
```

## Quick Start

```python
import plain_config

# Write configuration
config = {
    'hostname': 'example.com',
    'port': 8080,
    'timeout': 30.5,
    'debug': True,
    'api_key': b'secret_bytes',
    'tags': ['web', 'api', 'production']
}

plain_config.write_config('myapp.conf', config)

# Read configuration
loaded_config, structure = plain_config.read_config('myapp.conf')

# Update preserving structure
loaded_config['port'] = 9000
plain_config.write_config('myapp.conf', loaded_config, structure)
```

The resulting `myapp.conf` file looks like:

```ini
hostname=example.com
port/i=8080
timeout/f=30.5
debug/r=True
api_key/32=ONSWG4TFMRSW4ZBANVQWY3B5
tags/r=['web', 'api', 'production']
```

## File Format

### Basic Syntax

```ini
# Comments start with hash
key=value                    # Plain string
key/modifier=value           # Value with type conversion
key/mod1mod2=value          # Multiple modifiers (applied left-to-right)

# Empty lines are preserved
```

### Type Modifiers

When writing, `plain-config` automatically selects the appropriate type modifier. When reading, modifiers control type conversion:

| Modifier | Type | Description | Example |
|----------|------|-------------|---------|
| (none) | `str` | Plain string | `name=John` |
| `/i` | `int` | Integer | `port/i=8080` |
| `/f` | `float` | Float | `pi/f=3.14159` |
| `/r` | literal/nested | Python literals using `ast.literal_eval()` - supports bool, None, numbers, strings, bytes, tuples, lists, dicts, sets with safe nesting | `debug/r=True` or `data/r={'nested': [1, 2, 3]}` |
| `/s` | `str` | String (with UTF-8 encoding) | `text/s=hello` |
| `/b` | `bytes` | Bytes (UTF-8 encoded) | `data/b=binary` |
| `/32` | `bytes` | Base32 decoded | `key/32=MZXW6===` |
| `/64` | `bytes` | Base64 decoded | `data/64=aGVsbG8=` |
| `/p` | object | Unpickled Python object | `obj/p=...` |
| `/64p` | object | Base64 + pickle (for objects that can't use `/r`) | `list/64p=...` |
| `/C<char>` | continuation | Indicates the value was split across multiple lines using `<char>` as the continuation marker; combined with another modifier | `notes/C|r=first chunk|\nsecond chunk` |

Note that pickling/unpickling , that is, the '/p' modifier, will be performed only if `safe=False` is
passed to the calls.

#### Continuation Modifier `/C`

`plain-config` automatically inserts `/C<char>` when a value would exceed the configured line length (default 72 characters). The continuation character (taken from a pool of safe glyphs such as `|`, `⤸`, `→`) is appended to every intermediate chunk; on read, the parser strips the trailing marker and concatenates the following line until the marker disappears. A file might therefore contain:

```
description/C|r=first paragraph|\ncontinued text|\nfinal line
```

You rarely need to author `/C` by hand, but if you do, keep the same `<char>` throughout the wrapped value and ensure each continued line ends with that marker except the last.

### Automatic Type Selection

When writing configuration, `plain-config` automatically chooses the best encoding:

```python
{
    'simple_string': 'hello',            # → simple_string=hello
    'multiline': 'line1\nline2',         # → multiline/r='line1\nline2'
    'pickleme':'forward \f backward \b', # → pickleme/64s=Zm9yd2FyZCAMIGJhY2t3YXJkIAg=
    'integer': 42,                       # → integer/i=42
    'float': 3.14,                       # → float/f=3.14
    'boolean': True,                     # → boolean/r=True
    'none_value': None,                  # → none_value/r=None
    'binary': b'bytes',                  # → binary/32=MJQXGZIK
    'complex': {'nested': [1, 2, 3]},    # → complex/r={'nested': [1, 2, 3]}
    'with_class': {'obj': MyClass()}     # → with_class/64p=... (uses pickle)
}
```

**Note**: Nested structures (dicts, lists, tuples, sets) containing only safe types (str, bytes, int, float, bool, None)
are encoded using `/r` and decoded with `ast.literal_eval()` for security.
Objects that can't be represented this way (custom classes, functions, etc.) fall back to `/64p` , that is, base64 encoded pickle.

## API Reference

### `write_config(infofile, db, sdb=[], safe=True, rewrite_old=False, split_long_lines=72, continuation_chars=None)`

Write configuration data to file with automatic type encoding.

**Parameters:**
- `infofile`: File path (str/Path) or file object to write to
- `db`: Dictionary of key-value pairs to write
- `sdb`: Structure database from previous `read_config()` (preserves formatting)
- `safe`:  if `False`, allow pickling
- `rewrite_old`: If True, preserve keys in `sdb` not present in `db`
- `split_long_lines`: Maximum length (characters) before emitting a `/C` continuation; set to `0`/`None` to disable wrapping
- `continuation_chars`: String of candidate continuation glyphs; defaults to an internal sequence such as `\|⤸;↓↘→⟶⇒⇨⇩▼▽◢◣⤵║│┃┆┇┊┋∣⎟⎢⎥`

**Example:**
```python
config = {'host': 'localhost', 'port': 8080}
plain_config.write_config('server.conf', config)
```

### `read_config(infofile, safe=True)`

Read configuration data from file with automatic type decoding.

**Parameters:**
- `infofile`: File path (str/Path) or file object to read from
- `safe`: if `False`, allow unpickling

**Returns:**
- `db`: Dictionary of decoded key-value pairs
- `sdb`: Structure database (for preserving format when rewriting),
   it is a list of triples `(key,value,line)`,
   a comment line is represented by `(None,None,line)`,
   a line that could not be parsed is represented by `(False,False,line)`.

**Example:**
```python
config, structure = plain_config.read_config('server.conf')
print(config['port'])  # Automatically converted to int
```

## Examples

### Basic Configuration File

```python
import plain_config

# Application configuration
config = {
    'app_name': 'MyApp',
    'version': '1.0.0',
    'host': '0.0.0.0',
    'port': 8080,
    'debug': False,
    'max_connections': 100,
    'timeout': 30.0
}

plain_config.write_config('app.conf', config)
```

### Preserving Comments and Structure

```python
# Read existing config (with comments)
config, structure = plain_config.read_config('app.conf')

# Modify values
config['port'] = 9000
config['debug'] = True

# Write back preserving comments and order
plain_config.write_config('app.conf', config, structure)
```

### Working with Binary Data

```python
import plain_config

# Store API keys, tokens, etc.
secrets = {
    'api_key': b'\x00\x01\x02\x03\x04\x05',
    'token': b'secret_token_bytes',
    'salt': b'\xff\xfe\xfd\xfc'
}

plain_config.write_config('secrets.conf', secrets)

# Read back as bytes
loaded_secrets, _ = plain_config.read_config('secrets.conf')
assert isinstance(loaded_secrets['api_key'], bytes)
```

### Complex Objects (Lists, Dicts, etc.)

```python
import plain_config

# Store complex Python objects
config = {
    'database': {
        'host': 'localhost',
        'port': 5432,
        'credentials': {'user': 'admin', 'pass': 'secret'}
    },
    'servers': ['web1.example.com', 'web2.example.com'],
    'features': {'api', 'web', 'mobile'}
}

plain_config.write_config('complex.conf', config)

# Read back with full type fidelity
loaded, _ = plain_config.read_config('complex.conf')
assert isinstance(loaded['servers'], list)
assert isinstance(loaded['features'], set)
```

### File Permissions

Configuration files are created with restrictive permissions (0o600 = rw-------) for security:

```python
import plain_config
import os

config = {'api_secret': 'sensitive_data'}
plain_config.write_config('secure.conf', config)

# Check permissions
stat = os.stat('secure.conf')
print(oct(stat.st_mode)[-3:])  # Output: 600
```

## Why plain-config?

### Comparison with Other Formats

| Feature | plain-config | JSON | YAML | INI | TOML |
|---------|-------------|------|------|-----|------|
| Human-editable | ✅ Excellent | ⚠️ OK | ✅ Good | ✅ Good | ✅ Good |
| Comments | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Type preservation | ✅ Automatic | ✅ Manual | ⚠️ Ambiguous | ❌ Strings only | ✅ Explicit |
| Binary data | ✅ Native | ⚠️ Base64 | ⚠️ Manual | ❌ No | ❌ No |
| Dependencies | ✅ None | ✅ stdlib | ❌ PyYAML | ✅ stdlib | ❌ tomli |
| Structure preservation | ✅ Yes | ❌ No | ❌ No | ⚠️ Limited | ❌ No |
| Complex objects | ✅ Safe literals + Pickle | ❌ No | ⚠️ Limited | ❌ No | ⚠️ Limited |

### Use Cases

**Perfect for:**
- Application configuration files
- User preferences
- Server settings
- API credentials and secrets
- Any config that users might edit manually

**Not recommended for:**
- Large datasets (use databases)
- Sharing config between different languages (use JSON/YAML)
- Untrusted input (pickle security concerns)
- Strict schemas (use TOML/JSON with validators)

## Security Considerations

- **File permissions**: Config files are created with mode 0o600 (owner read/write only)
- **Safe by default**: By default, both `read_config()` and `write_config()` use `safe=True`, which:
  - **Reading**: Refuses to unpickle `/p` or `/64p` values (will skip them)
  - **Writing**: Raises `RuntimeError` if a value cannot be safely encoded (requires `safe=False` to use pickle)
  - Uses `ast.literal_eval()` for `/r` modifier, which only evaluates Python literals (strings, numbers, tuples, lists, dicts, booleans, None, bytes) - safe for untrusted input
- **Pickle usage**: The `/p` and `/64p` modifiers use `pickle` for objects that can't be represented as literals (custom classes, functions, etc.). To enable pickle:
  - Set `safe=False` when calling `read_config()` or `write_config()`
  - Only use `safe=False` with config files from trusted sources, as pickle can execute arbitrary code when deserializing malicious data
- **Automatic safety**: When writing config with `safe=True` (default), plain-config automatically prefers `/r` (safe) over `/64p` (pickle) whenever possible, and fails if pickle would be needed

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## License

MIT License - see [LICENSE](LICENSE) file for details

## Tests

The code is tested
[using  *GitHub actions*](https://github.com/mennucc/plain_config/actions/workflows/test.yaml)
inside an Ubuntu environment, for Python 3.8 up to 3.13 (but not yet with 3.14).

![Test results](https://github.com/mennucc/plain_config/actions/workflows/test.yaml/badge.svg)


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

If you wish to help in developing, please

    pip -r requirements-test.txt
    git config --local core.hooksPath .githooks/

so that each commit is pre tested.

## Author

Andrea C G Mennucci

## Links

- **GitHub**: https://github.com/mennucc/plain-config
- **PyPI**: https://pypi.org/project/plain-config/
- **Issues**: https://github.com/mennucc/plain-config/issues

## Acknowledgments

[Claude Code](https://claude.ai/claude-code) by [Anthropic](https://www.anthropic.com/) was used to debug and enhance this package.

Development was done using [Wing Python IDE](https://wingware.com/) by Wingware.
