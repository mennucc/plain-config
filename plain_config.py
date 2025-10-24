#!/usr/bin/env python3

"""
Simple Configuration File Parser

This module provides a simple yet flexible configuration file format with automatic
type conversion and encoding support.

File Format
-----------
The configuration file uses a key/value format with optional type modifiers:

    key=value                    # Plain string value
    key/modifier=value           # Value with type conversion
    key/modifier1modifier2=value # Multiple modifiers applied in sequence
    # comment                    # Comments (lines starting with #)

Supported Type Modifiers
------------------------
- No modifier: Plain string
- i: Convert to integer
- f: Convert to float
- r: Evaluate as Python literal (for True, False, None, etc.)
- s: Convert to string (with UTF-8 encoding)
- b: Convert to bytes (with UTF-8 encoding)
- 32: Base32 decode
- 64: Base64 decode
- p: Unpickle (deserialize Python object)

Modifiers can be combined and are applied left-to-right. For example:
- key/64p=... means base64 decode, then unpickle
- key/32b=... means base32 decode, then convert to bytes

Automatic Encoding
------------------
When writing values, the module automatically selects appropriate encoding:
- Strings with control characters → base64 encoded (/64s)
- Bytes → base32 encoded (/32)
- Booleans and None → repr format (/r)
- Integers → int format (/i)
- Floats → float format (/f)
- Complex objects → pickled and base64 encoded (/64p)

Example Usage
-------------
    >>> import plain_config
    >>>
    >>> # Write configuration
    >>> data = {
    ...     'hostname': 'example.com',
    ...     'port': 8080,
    ...     'timeout': 30.5,
    ...     'enabled': True,
    ...     'key': b'secret_bytes',
    ...     'metadata': {'version': 1, 'author': 'user'}
    ... }
    >>> plain_config.write_config('config.txt', data)
    >>>
    >>> # Read configuration
    >>> loaded_data, structure = plain_config.read_config('config.txt')
    >>> assert loaded_data == data
    >>>
    >>> # Update configuration preserving structure
    >>> loaded_data['port'] = 9000
    >>> plain_config.write_config('config.txt', loaded_data, structure)

Functions
---------
- write_config(infofile, db, sdb=[], rewrite_old=False)
    Write configuration data to file

- read_config(infofile)
    Read configuration data from file

"""

__all__ = ('write_config', 'read_config')

import os
import pickle
import base64
import copy
import logging
import ast
from pathlib import Path

logger = logging.getLogger(__name__)

default_chmod = 0o600

_eval_safe_item = (str, bytes, int, float, bool)
_eval_safe_recurse = (tuple, list, set)

def _check_eval_safe(S):
    if S is None or  any (isinstance(S, t) for t in _eval_safe_item):
        return True
    if isinstance(S, dict):
        return all( (_check_eval_safe(k) and  _check_eval_safe(v))
                    for k, v in S.items())
    if any (isinstance(S, t) for t in _eval_safe_recurse):
        return all(  _check_eval_safe(v)    for v in S)
    return False



def mychmod(f, mode=default_chmod):
    """Set file permissions, with error handling."""
    try:
        os.chmod(f, mode)
    except Exception as E:
        logger.exception('Why cant I set chmod %r on %r', mode, f)

def write_config(infofile, db, sdb=[], safe=True, rewrite_old = False):
    """
    Write configuration data to a file with automatic type encoding.

    This function writes key-value pairs to a configuration file, automatically
    selecting appropriate encoding based on the value type. It can preserve the
    original file structure (comments, ordering) if a structure database is provided.

    Parameters
    ----------
    infofile : str, bytes, Path, or file object
        The configuration file to write to. Can be:
        - A file path (str, bytes, or Path): File will be created/overwritten
        - A file object: Data will be written to the open file

        When a path is provided, the file is created with 0o600 permissions
        for security.

    db : dict
        Dictionary of key-value pairs to write. Keys must be strings without
        '=' or '/' characters. Values are automatically encoded based on type:
        - str (with control chars) → base64 encoded (/64s)
        - str (plain) → plain text
        - bool or None → repr format (/r)
        - int → integer format (/i)
        - float → float format (/f)
        - bytes → base32 encoded (/32)
        - other objects → pickled and base64 encoded (/64p)

    sdb : list of tuples, optional
        Structure database from a previous read_config() call. Used to preserve
        the original file structure (key ordering, comments, empty lines).
        Each tuple is (key, modifier, original_line). Default is empty list.

        When provided, keys that were in the original file are written in their
        original positions, and comments/empty lines are preserved.

    safe: bool
        if False, allow pickling

    rewrite_old : bool, optional
        If True, keys in sdb that are not in db are written back using
        their original lines. If False (default), such keys are omitted.

        Use True to preserve old configuration entries that were not modified.

    Returns
    -------
    None

    Raises
    ------
    AssertionError
        If any key in db contains '=' or '/' characters.

    Examples
    --------
    Write new configuration:

        >>> data = {'host': 'localhost', 'port': 8080, 'debug': True}
        >>> write_config('config.txt', data)

    Update configuration preserving structure:

        >>> loaded_data, structure = read_config('config.txt')
        >>> loaded_data['port'] = 9000
        >>> write_config('config.txt', loaded_data, structure)

    Write to file object:

        >>> with open('config.txt', 'w') as f:
        ...     write_config(f, data)

    Notes
    -----
    - When writing to a file path, the file is created with mode 0o600 (read/write
      for owner only) for security.
    - Keys are written in the order they appear in sdb first, then any new keys
      from db are appended.
    - Binary data is base32-encoded rather than base64 to avoid issues with
      case-insensitive filesystems.
    """
    if isinstance(infofile, (str, bytes, Path)): 
        with open(infofile,'w') as F:
            mychmod(infofile)
            write_config(F, db, sdb, safe, rewrite_old)
        return
    F = infofile
    #
    def write_k_v(k,v,F):
        assert isinstance(k,str) and '=' not in k and '/' not in k
        if isinstance(v,str):
            if any( (ord(j)<32)  for j in v ):
                v = v.encode('utf8')
                v = base64.b64encode(v)
                v = v.decode()
                F.write('{}/64s={}\n'.format(k, v))
            else:
                F.write('{}={}\n'.format(k,v))
        elif isinstance(v, bool) or v is None:
            F.write('{}/r={!r}\n'.format(k,v))
        elif isinstance(v,int):
            F.write('{}/i={}\n'.format(k,v))
        elif isinstance(v,float):
            F.write('{}/f={!r}\n'.format(k,v))
        elif isinstance(v,bytes):
            F.write('{}/32={}\n'.format(k, base64.b32encode(v).decode('ascii')))
        elif _check_eval_safe(v):
            F.write('{}/r={!r}\n'.format(k,v))
            # will use ast.literal_eval for decoding
        elif not safe:
            F.write('{}/64p={}\n'.format(k, base64.b64encode(pickle.dumps(v)).decode('ascii')))
        else:
            raise RuntimeError('cannot write {!r}, `safe` is True'.format(v))
    #
    db = copy.copy(db)
    # write keys that were in file, in same position
    for k,m,l in sdb:
        if k and k in db:
            write_k_v(k,db[k],F)
            db.pop(k)
        elif k and rewrite_old:
            F.write(l)
        # invalid lines are not rewritten
        elif k is None:
            F.write(l)
    # write new keys
    for k in db.keys():
        write_k_v(k,db[k],F)


def read_config(infofile, safe=True):
    """
    Read configuration data from a file with automatic type decoding.

    This function reads key-value pairs from a configuration file, automatically
    decoding values based on their type modifiers. It also returns the file
    structure, which can be used to preserve formatting when writing updates.

    Parameters
    ----------
    infofile : str, bytes, Path, or file object
        The configuration file to read from. Can be:
        - A file path (str, bytes, or Path): File will be opened and read
        - A file object or iterable: Must yield text lines

    safe: bool
        `True` by default; if False, allow  unpickling of /p keys; set to False only for trusted input

    Returns
    -------
    db : dict
        Dictionary of decoded key-value pairs. Keys are strings, values are
        decoded according to their type modifiers:
        - /i → int
        - /f → float
        - /r → Python literal (True, False, None, etc.)
        - /s → str (UTF-8 decoded)
        - /b → bytes (UTF-8 encoded)
        - /32 → base32 decoded
        - /64 → base64 decoded
        - /p → unpickled Python object
        - (no modifier) → plain string

    sdb : list of tuples
        Structure database preserving the original file format. Each tuple
        contains (key, modifier, original_line):
        - key: The configuration key (str), or None for comments/empty lines,
               or False for invalid lines
        - modifier: The type modifier string (str)
        - original_line: The complete original line including newline

        Use this when calling write_config() to preserve file structure.

    Examples
    --------
    Read configuration file:

        >>> data, structure = read_config('config.txt')
        >>> print(data['hostname'])
        'example.com'
        >>> print(data['port'])
        8080

    Read and update configuration:

        >>> data, structure = read_config('config.txt')
        >>> data['port'] = 9000
        >>> data['new_key'] = 'new_value'
        >>> write_config('config.txt', data, structure)

    Read from file object:

        >>> with open('config.txt') as f:
        ...     data, structure = read_config(f)

    Read from StringIO:

        >>> from io import StringIO
        >>> config_text = "host=localhost\\nport/i=8080\\n"
        >>> data, structure = read_config(StringIO(config_text))

    Notes
    -----
    - Comments (lines starting with #) and empty lines are preserved in sdb
      with key=None.
    - Invalid lines (no '=' character) are logged as warnings and stored in sdb
      with key=False.
    - Lines with parse errors are logged but processing continues.
    - Modifiers are applied left-to-right, so /64p means base64 decode then unpickle.
    - The file must be UTF-8 encoded or compatible.

    See Also
    --------
    write_config : Write configuration data to file
    _read_config : Internal function that does the actual parsing
    """
    if isinstance(infofile, (str,bytes, Path)):
        with open(infofile) as F:
            db = _read_config(F, safe)
        return db
    return  _read_config(infofile, safe)

def _read_config(infofile, safe):
    " infofile must iterate to text lines; returns (db, sdb) where db are the extracted key,value, sdb is the structure of the file"
    def B(x): # to byte
        if isinstance(x, str):
            return x.encode('utf8')
        return x
    db = {}
    sdb = []
    for line_ in infofile:
        line = line_.rstrip('\n\r')
        # skip comments and empty lines
        if not line.strip() or line.strip().startswith('#'):
            sdb.append( (None, None, line_) )
            continue
        if '=' not in line:
            logger.warning('In info file %r ignored line %r', infofile, line)
            sdb.append( (False, False, line_) )
            continue
        try:
            key,value = line.split('=',1)
            m=''
            if '/' in key:
                key,m = key.split('/',1)
            sdb.append( (key, m, line_) )
            while m:
                if m.startswith('p'):
                    if safe:
                        logger.error('cannot read %r, `safe` is True', line)
                        m = False
                        break
                    value = pickle.loads(B(value))
                    m = m[1:]
                elif m.startswith('s'):
                    if isinstance(value, bytes):
                        value = value.decode('utf8')
                    elif isinstance(value, int):
                        value = str(value)
                    else:
                        logger.warning('Cannot convert to string the value : %r', value)
                    m = m[1:]
                elif m.startswith('b'):
                    if isinstance(value, str):
                        value = value.encode('utf8')
                    #elif isinstance(value, int):
                    #    value = value.to_bytes(....)
                    else:
                        logger.warning('Cannot convert to bytes the value : %r', value)
                    m = m[1:]
                elif m.startswith('i'):
                    value = int(value)
                    m = m[1:]
                elif m.startswith('f'):
                    value = float(value)
                    m = m[1:]
                elif m.startswith('r'):
                    value = ast.literal_eval(value)
                    m = m[1:]
                elif m.startswith('32'):
                    value = base64.b32decode(B(value))
                    m = m[2:]
                elif m.startswith('64'):
                    value = base64.b64decode(B(value))
                    m = m[2:]
                else:
                    logger.error('error parsing line modifiers : %r', line)
                    m = False
                    break
            if m == '':
                db[key] = value
        except Exception as E:
            logger.warning('In info file %r error parsing  %r : %r', infofile, line, E)
    return db, sdb
