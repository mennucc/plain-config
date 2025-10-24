#!/usr/bin/env python3

"""
Unit tests for plain_config module

Tests all features of the plain configuration file format including:
- Reading and writing various data types
- Type modifiers and conversions
- Encoding/decoding (base32, base64, pickle)
- Structure preservation
- Comments and empty lines
- Error handling
"""

import os
import sys
import io
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path if running standalone
testdir = os.path.dirname(os.path.realpath(__file__))
sourcedir = os.path.dirname(testdir)
if sourcedir not in sys.path:
    sys.path.insert(0, sourcedir)

import plain_config


class TestPlainConfig(unittest.TestCase):
    """Test suite for plain_config module"""

    def setUp(self):
        """Create temporary directory for test files"""
        self.test_dir = tempfile.mkdtemp(prefix='test_plain_config_')

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.test_dir)

    def get_test_file(self, name='test_config.txt'):
        """Get path to test file in temporary directory"""
        return os.path.join(self.test_dir, name)

    def test_basic_string(self):
        """Test reading/writing plain string values"""
        config_file = self.get_test_file()
        data = {
            'hostname': ' example.com',
            'username': 'admin  ',
            'path': '/var/log/app.log'
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)

    def test_integer_values(self):
        """Test integer type conversion"""
        config_file = self.get_test_file()
        data = {
            'port': 8080,
            'max_connections': 100,
            'timeout_seconds': 30
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)
        self.assertIsInstance(loaded_data['port'], int)

    def test_float_values(self):
        """Test float type conversion"""
        config_file = self.get_test_file()
        data = {
            'timeout': 30.5,
            'threshold': 0.95,
            'pi': 3.14159
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)
        self.assertIsInstance(loaded_data['timeout'], float)

    def test_boolean_and_none(self):
        """Test boolean and None values"""
        config_file = self.get_test_file()
        data = {
            'enabled': True,
            'disabled': False,
            'optional': None
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)
        self.assertIsInstance(loaded_data['enabled'], bool)
        self.assertIsInstance(loaded_data['disabled'], bool)
        self.assertIsNone(loaded_data['optional'])

    def test_bytes_values(self):
        """Test bytes type encoding/decoding"""
        config_file = self.get_test_file()
        data = {
            'secret_key': b'my_secret_bytes',
            'binary_data': b'\x00\x01\x02\xff\xfe'
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)
        self.assertIsInstance(loaded_data['secret_key'], bytes)

    def test_string_with_special_chars(self):
        """Test strings containing control characters"""
        config_file = self.get_test_file()
        data = {
            'newline': 'line1\nline2',
            'tab': 'col1\tcol2',
            'null': 'before\x00after'
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)

    def test_complex_objects(self):
        """Test pickling complex Python objects"""
        config_file = self.get_test_file()
        data = {
            'list_data': [1, 2, 3, 'four', 5.0],
            'dict_data': {'nested': {'key': 'value'}},
            'tuple_data': (1, 'two', 3.0),
            'set_data': {1, 2, 3, 4, 5}
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data['list_data'], data['list_data'])
        self.assertEqual(loaded_data['dict_data'], data['dict_data'])
        self.assertEqual(loaded_data['tuple_data'], data['tuple_data'])
        self.assertEqual(loaded_data['set_data'], data['set_data'])

    def test_mixed_types(self):
        """Test configuration with mixed data types"""
        config_file = self.get_test_file()
        data = {
            'string': 'hello',
            'integer': 42,
            'float': 3.14,
            'boolean': True,
            'none_value': None,
            'bytes_value': b'binary',
            'list_value': [1, 2, 3],
            'dict_value': {'key': 'value'}
        }

        plain_config.write_config(config_file, data)
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)

    def test_structure_preservation(self):
        """Test that file structure (comments, order) is preserved"""
        config_file = self.get_test_file()

        # Write initial config with some data
        data1 = {'key1': 'value1', 'key2': 42}
        plain_config.write_config(config_file, data1)

        # Read it back to get structure
        loaded_data, structure = plain_config.read_config(config_file)

        # Modify and write again with structure
        loaded_data['key1'] = 'modified'
        loaded_data['key3'] = 'new_value'
        plain_config.write_config(config_file, loaded_data, structure)

        # Read again
        final_data, _ = plain_config.read_config(config_file)

        self.assertEqual(final_data['key1'], 'modified')
        self.assertEqual(final_data['key2'], 42)
        self.assertEqual(final_data['key3'], 'new_value')

    def test_comments_and_empty_lines(self):
        """Test that comments and empty lines are preserved"""
        config_file = self.get_test_file()

        # Manually create config with comments
        with open(config_file, 'w') as f:
            f.write('# This is a comment\n')
            f.write('\n')
            f.write('key1=value1\n')
            f.write('# Another comment\n')
            f.write('key2/i=42\n')
            f.write('\n')

        # Read config
        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data['key1'], 'value1')
        self.assertEqual(loaded_data['key2'], 42)

        # Check structure includes comments
        self.assertEqual(len(structure), 6)  # 2 comments + 2 keys + 2 empty lines

        # Write back with structure
        loaded_data['key1'] = 'modified'
        plain_config.write_config(config_file, loaded_data, structure)

        # Check comments still there
        with open(config_file) as f:
            content = f.read()
        self.assertIn('# This is a comment', content)
        self.assertIn('# Another comment', content)

    def test_path_object_as_filename(self):
        """Test using Path object for filename"""
        config_file = Path(self.get_test_file())
        data = {'test_key': 'test_value'}

        plain_config.write_config(config_file, data)
        loaded_data, _ = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)

    def test_file_object_write(self):
        """Test writing to file-like object"""
        config_file = self.get_test_file()
        data = {'key': 'value', 'number': 123}

        with open(config_file, 'w') as f:
            plain_config.write_config(f, data)

        loaded_data, _ = plain_config.read_config(config_file)
        self.assertEqual(loaded_data, data)

    def test_file_object_read(self):
        """Test reading from file-like object"""
        config_file = self.get_test_file()
        data = {'key': 'value', 'number': 123}

        plain_config.write_config(config_file, data)

        with open(config_file) as f:
            loaded_data, structure = plain_config._read_config(f)

        self.assertEqual(loaded_data, data)

    def test_empty_config(self):
        """Test reading empty configuration file"""
        config_file = self.get_test_file()

        # Create empty file
        with open(config_file, 'w') as f:
            pass

        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, {})
        self.assertEqual(structure, [])

    def test_only_comments(self):
        """Test configuration with only comments"""
        config_file = self.get_test_file()

        with open(config_file, 'w') as f:
            f.write('# Comment 1\n')
            f.write('# Comment 2\n')
            f.write('\n')

        loaded_data, structure = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, {})
        self.assertEqual(len(structure), 3)

    def test_rewrite_old_option(self):
        """Test rewrite_old parameter"""
        config_file = self.get_test_file()

        # Write initial config
        data1 = {'old_key': 'old_value', 'keep_key': 'keep_value'}
        plain_config.write_config(config_file, data1)

        # Read and get structure
        _, structure = plain_config.read_config(config_file)

        # Write new data WITHOUT rewrite_old (default behavior)
        data2 = {'keep_key': 'modified', 'new_key': 'new_value'}
        plain_config.write_config(config_file, data2, structure, rewrite_old=False)

        # Old key should be gone
        loaded_data, _ = plain_config.read_config(config_file)
        self.assertNotIn('old_key', loaded_data)
        self.assertEqual(loaded_data['keep_key'], 'modified')
        self.assertEqual(loaded_data['new_key'], 'new_value')

    def test_special_characters_in_values(self):
        """Test values with equals signs and other special characters"""
        config_file = self.get_test_file()
        data = {
            'equation': '2+2=4',
            'url': 'http://example.com?param=value&other=data',
            'spaces': '  leading and trailing  '
        }

        plain_config.write_config(config_file, data)
        loaded_data, _ = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)

    def test_unicode_strings(self):
        """Test Unicode strings"""
        config_file = self.get_test_file()
        data = {
            'emoji': '😀🎉🚀',
            'chinese': '你好世界',
            'arabic': 'مرحبا',
            'russian': 'Привет'
        }

        plain_config.write_config(config_file, data)
        loaded_data, _ = plain_config.read_config(config_file)

        self.assertEqual(loaded_data, data)

    def test_large_values(self):
        """Test handling of large values"""
        config_file = self.get_test_file()
        large_string = 'x' * 10000
        large_list = list(range(1000))

        data = {
            'large_string': large_string,
            'large_list': large_list
        }

        plain_config.write_config(config_file, data)
        loaded_data, _ = plain_config.read_config(config_file)

        self.assertEqual(loaded_data['large_string'], large_string)
        self.assertEqual(loaded_data['large_list'], large_list)

    def test_key_ordering_preserved(self):
        """Test that key ordering is preserved when using structure"""
        config_file = self.get_test_file()

        # Write with specific order
        from collections import OrderedDict
        data = OrderedDict([
            ('first', 1),
            ('second', 2),
            ('third', 3),
            ('fourth', 4)
        ])

        plain_config.write_config(config_file, data)

        # Read file and check order
        with open(config_file) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        self.assertEqual(lines[0], 'first/i=1')
        self.assertEqual(lines[1], 'second/i=2')
        self.assertEqual(lines[2], 'third/i=3')
        self.assertEqual(lines[3], 'fourth/i=4')

    def test_invalid_key_names(self):
        """Test that invalid key names (with = or /) raise errors"""
        config_file = self.get_test_file()

        # Keys with equals should fail during write
        data = {'invalid=key': 'value'}
        with self.assertRaises(AssertionError):
            plain_config.write_config(config_file, data)

        # Keys with slash should fail during write
        data = {'invalid/key': 'value'}
        with self.assertRaises(AssertionError):
            plain_config.write_config(config_file, data)

        # Keys must be string
        data = {False : 'value'}
        with self.assertRaises(AssertionError):
            plain_config.write_config(config_file, data)


    def test_file_permissions(self):
        """Test that written files have correct permissions (0o600)"""
        config_file = self.get_test_file()
        data = {'key': 'value'}

        plain_config.write_config(config_file, data)

        # Check file permissions (only on Unix-like systems)
        if hasattr(os, 'stat'):
            stat_info = os.stat(config_file)
            permissions = stat_info.st_mode & 0o777
            self.assertEqual(permissions, 0o600)


    def test_string_io(self):
        F = io.StringIO()
        data = {'binary': b'test_bytes'}
        plain_config.write_config(F, data)
        F.seek(0)
        loaded_data, _ = plain_config.read_config(F)
        self.assertEqual(loaded_data, data)


class TestModifierCombinations(unittest.TestCase):
    """Test various combinations of type modifiers"""

    def setUp(self):
        """Create temporary directory for test files"""
        self.test_dir = tempfile.mkdtemp(prefix='test_modifiers_')

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.test_dir)

    def get_test_file(self, name='test_modifiers.txt'):
        """Get path to test file in temporary directory"""
        return os.path.join(self.test_dir, name)

    def test_base64_pickle_combination(self):
        """Test /64p modifier combination (base64 + pickle)"""
        config_file = self.get_test_file()

        # Write complex object (will use /r automatically)
        data = {'complex': {'nested': [1, 2, Exception]}}
        plain_config.write_config(config_file, data)
        
        # Verify file contains /64p
        with open(config_file) as f:
            content = f.read()
        self.assertIn('/64p=', content)

        # Read back
        loaded_data, _ = plain_config.read_config(config_file)
        self.assertEqual(loaded_data, data)


    def test_ast_combination(self):
        """Test /r modifier combination (will use ast.literal_eval)"""
        config_file = self.get_test_file()

        # Write complex object (will use /r automatically)
        data = {'complex': {'nested': [1, 2, 3]}}
        plain_config.write_config(config_file, data)

        # Verify file contains /64p
        with open(config_file) as f:
            content = f.read()
        self.assertIn('/r=', content)

        # Read back
        loaded_data, _ = plain_config.read_config(config_file)
        self.assertEqual(loaded_data, data)

    def test_base32_encoding(self):
        """Test base32 encoding for bytes"""
        config_file = self.get_test_file()

        # Write bytes (will use /32 automatically)
        data = {'binary': b'test_bytes'}
        plain_config.write_config(config_file, data)

        # Verify file contains /32
        with open(config_file) as f:
            content = f.read()
        self.assertIn('/32=', content)

        # Read back
        loaded_data, _ = plain_config.read_config(config_file)
        self.assertEqual(loaded_data, data)


if __name__ == '__main__':
    unittest.main()
