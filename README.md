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
tags/64p=gASVHgAAAAAAAABdlCiMA3dlYpSMA2FwaZSMCnByb2R1Y3Rpb26UZS4=
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
| `/r` | literal | Python literal (True/False/None) | `debug/r=True` |
| `/s` | `str` | String (with UTF-8 encoding) | `text/s=hello` |
| `/b` | `bytes` | Bytes (UTF-8 encoded) | `data/b=binary` |
| `/32` | `bytes` | Base32 decoded | `key/32=MZXW6===` |
| `/64` | `bytes` | Base64 decoded | `data/64=aGVsbG8=` |
| `/p` | object | Unpickled Python object | `obj/p=...` |
| `/64p` | object | Base64 + pickle (complex objects) | `list/64p=...` |

### Automatic Type Selection

When writing configuration, `plain-config` automatically chooses the best encoding:

```python
{
    'simple_string': 'hello',           # → simple_string=hello
    'multiline': 'line1\nline2',        # → multiline/64s=bGluZTEKbGluZTI=
    'integer': 42,                       # → integer/i=42
    'float': 3.14,                       # → float/f=3.14
    'boolean': True,                     # → boolean/r=True
    'none_value': None,                  # → none_value/r=None
    'binary': b'bytes',                  # → binary/32=MJQXGZIK
    'complex': {'nested': [1, 2, 3]}    # → complex/64p=...
}
```

## API Reference

### `write_config(infofile, db, sdb=[], rewrite_old=False)`

Write configuration data to file with automatic type encoding.

**Parameters:**
- `infofile`: File path (str/Path) or file object to write to
- `db`: Dictionary of key-value pairs to write
- `sdb`: Structure database from previous `read_config()` (preserves formatting)
- `rewrite_old`: If True, preserve keys in `sdb` not present in `db`

**Example:**
```python
config = {'host': 'localhost', 'port': 8080}
plain_config.write_config('server.conf', config)
```

### `read_config(infofile)`

Read configuration data from file with automatic type decoding.

**Parameters:**
- `infofile`: File path (str/Path) or file object to read from

**Returns:**
- `db`: Dictionary of decoded key-value pairs
- `sdb`: Structure database (for preserving format when rewriting)

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
| Complex objects | ✅ Pickle | ❌ No | ⚠️ Limited | ❌ No | ⚠️ Limited |

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
- **Pickle usage**: The `/p` modifier uses `pickle` for complex objects. Only use with trusted config files
- **Input validation**: For untrusted input, consider using the `/r` modifier which uses `ast.literal_eval()` instead of `eval()`

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## License

MIT License - see [LICENSE](LICENSE) file for details

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
