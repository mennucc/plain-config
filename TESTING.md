# Testing Guide for plain-config

This document explains how to run tests for the plain-config package.

## Quick Start

```bash
# Install testing dependencies
pip install -r requirements-test.txt

# Run tests for current Python version
python -m unittest discover -s unittests -p "test_*.py" -v

# Or run the test file directly (it's executable)
./unittests/test_plain_config.py -v
```

## Using Tox (Multi-Version Testing)

Tox tests your package across multiple Python versions automatically.

### Install Tox

```bash
pip install tox
```

### Run All Tests

```bash
# Test across all Python versions (3.6-3.13)
tox

# Test specific Python version
tox -e py310

# Test only what's available (skip missing interpreters)
tox --skip-missing-interpreters
```

### Available Tox Environments

| Environment | Description | Command |
|-------------|-------------|---------|
| `py36-py313` | Test on Python 3.6 through 3.13 | `tox` |
| `flake8` | Minimal linting (E9,F63,F7,F82) | `tox -e flake8` |
| `flake8-full` | Comprehensive linting | `tox -e flake8-full` |
| `coverage` | Code coverage report | `tox -e coverage` |
| `black` | Check code formatting | `tox -e black` |
| `mypy` | Type checking | `tox -e mypy` |

### Examples

```bash
# Test on Python 3.10 and 3.11 only
tox -e py310,py311

# Run linting
tox -e flake8

# Generate coverage report
tox -e coverage
# Opens htmlcov/index.html

# Check formatting
tox -e black

# Run all quality checks
tox -e flake8,black,mypy
```

## Pre-Commit Hook

The repository includes a pre-commit hook that automatically:
1. Prevents file mode changes
2. Runs flake8 on staged changes
3. Runs all executable tests

### Enable Pre-Commit Hook

```bash
# Install dependencies
pip install -r requirements-test.txt

# Enable the hook
git config --local core.hooksPath .githooks/

# Now every commit will run tests automatically!
```

### Hook Behavior

The pre-commit hook creates a clean test environment:
- Uses `git archive` to export staged files
- Applies staged changes with `patch`
- Runs flake8 with minimal checks: `E9,F63,F7,F82`
- Runs all executable test files in `unittests/`

### Bypass Hook (Emergency Only)

```bash
# Skip pre-commit checks (not recommended)
git commit --no-verify
```

## Manual Testing

### Run All Tests

```bash
# Using unittest discovery
python -m unittest discover -s unittests -p "test_*.py" -v

# Run specific test file
python unittests/test_plain_config.py

# Run specific test class
python -m unittest unittests.test_plain_config.TestPlainConfig

# Run specific test method
python -m unittest unittests.test_plain_config.TestPlainConfig.test_basic_string
```

### Run with Coverage

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run -m unittest discover -s unittests -p "test_*.py"

# Show coverage report
coverage report -m

# Generate HTML report
coverage html
# Opens htmlcov/index.html
```

### Linting

```bash
# Install flake8
pip install flake8

# Minimal checks (as in pre-commit hook)
flake8 . --select=E9,F63,F7,F82

# Full checks
flake8 . --max-line-length=120
```

## Continuous Integration

For CI/CD systems (GitHub Actions, GitLab CI, etc.), use tox:

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - run: pip install tox
    - run: tox -e py$(echo ${{ matrix.python-version }} | tr -d .)
```

### GitLab CI Example

```yaml
test:
  image: python:3.10
  script:
    - pip install tox
    - tox
```

## Test Structure

### Test Organization

```
unittests/
└── test_plain_config.py  # 24 comprehensive tests
    ├── TestPlainConfig
    │   ├── test_basic_string
    │   ├── test_integer_values
    │   ├── test_float_values
    │   ├── test_boolean_and_none
    │   ├── test_bytes_values
    │   ├── test_string_with_special_chars
    │   ├── test_complex_objects
    │   ├── test_mixed_types
    │   ├── test_structure_preservation
    │   ├── test_comments_and_empty_lines
    │   ├── test_path_object_as_filename
    │   ├── test_file_object_write
    │   ├── test_file_object_read
    │   ├── test_empty_config
    │   ├── test_only_comments
    │   ├── test_rewrite_old_option
    │   ├── test_special_characters_in_values
    │   ├── test_unicode_strings
    │   ├── test_large_values
    │   ├── test_key_ordering_preserved
    │   ├── test_invalid_key_names
    │   └── test_file_permissions
    └── TestModifierCombinations
        ├── test_base64_pickle_combination
        └── test_base32_encoding
```

### Test Coverage

Current test coverage: **100%** of main functionality

Tests cover:
- ✅ All data types (str, int, float, bool, None, bytes, objects)
- ✅ All type modifiers (i, f, r, s, b, 32, 64, p, 64p)
- ✅ Structure preservation (comments, empty lines, ordering)
- ✅ File operations (paths, Path objects, file objects)
- ✅ Edge cases (empty files, invalid keys, large values, Unicode)
- ✅ Security (file permissions)

## Adding New Tests

### Template for New Test

```python
def test_your_feature(self):
    """Test description"""
    config_file = self.get_test_file()
    data = {'key': 'value'}

    plain_config.write_config(config_file, data)
    loaded_data, structure = plain_config.read_config(config_file)

    self.assertEqual(loaded_data, data)
```

### Running Your New Test

```bash
# Run just your new test
python -m unittest unittests.test_plain_config.TestPlainConfig.test_your_feature -v

# Run all tests to make sure nothing broke
python -m unittest discover -s unittests -v

# Run tox to test across Python versions
tox
```

## Troubleshooting

### Tests Fail on Import

**Problem**: `ModuleNotFoundError: No module named 'plain_config'`

**Solution**: Install in development mode:
```bash
pip install -e .
```

### Tox Can't Find Python Version

**Problem**: `ERROR: InterpreterNotFound: python3.11`

**Solution**: Install missing Python version or skip:
```bash
tox --skip-missing-interpreters
```

### Pre-Commit Hook Fails

**Problem**: Tests pass manually but fail in hook

**Solution**: The hook tests in a clean environment. Make sure all changes are staged:
```bash
git add .
git status  # Check what will be tested
```

### Permission Denied on Test File

**Problem**: `Permission denied: ./unittests/test_plain_config.py`

**Solution**: Make test executable:
```bash
chmod +x unittests/test_plain_config.py
```

## Best Practices

1. **Run tests before committing**: The pre-commit hook does this automatically
2. **Test across Python versions**: Use `tox` before releasing
3. **Check coverage**: Aim for 100% coverage of critical paths
4. **Write descriptive test names**: `test_feature_name_behavior`
5. **One assertion per test**: Makes failures easier to diagnose
6. **Use setUp/tearDown**: Clean up temporary files

## Resources

- **unittest documentation**: https://docs.python.org/3/library/unittest.html
- **tox documentation**: https://tox.wiki/
- **flake8 documentation**: https://flake8.pycqa.org/
- **coverage documentation**: https://coverage.readthedocs.io/
