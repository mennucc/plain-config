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

logger = logging.getLogger('plain-config')

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

def _is_ctrl(c):
    """Return True if character c is a control character."""
    if not c:
        return False
    if isinstance(c, str):
        code = ord(c)
    else:
        code = c
    assert  isinstance(code, int)
    # C0 controls (0-31) and DEL (127) and C1 controls (128-159)
    return (0x00 <= code <= 0x1F) or (0x7F <= code <= 0x9F)

def _is_ctrl_but_rnc(c):
    """Return True if character c is a control character, but not \r \t \n."""
    if not c:
        return False
    if isinstance(c, str):
        code = ord(c)
    else:
        code = c
    assert  isinstance(code, int)
    return ( (0x00 <= code <= 0x1F) and (code not in (9, 13, 10))) or (0x7F <= code <= 0x9F)

funny_continuation_chars = r'\|⤸;↓↘→⟶⇒⇨⇩▼▽◢◣⤵║│┃┆┇┊┋∣⎟⎢⎥'

def _write_split(F, m, k, v, split_long_lines, continuation_chars):
    """Render a single line, adding `/C<char>` when `value` would exceed `split_long_lines`."""
    if not split_long_lines or \
       (len(v) + len(k) + len(m) + 2) < split_long_lines:
        if m:
            m = '/' + m
        F.write(k + m + '='+ v + '\n')
        return
    cont = None
    for c in  continuation_chars:
        if c not in v:
            cont = c
            break
    if cont is None:
        logger.error('cannot split %r', v)
        if m:
            m = '/' + m
        F.write(k + m + '='+ v + '\n')
        return
    m = '/C' + cont + m
    pre = (len(k) + len(m) + 2)
    F.write(k + m + '=')
    while (pre + len(v)) > split_long_lines:
        l = max(split_long_lines - pre, 2)
        # find a nicer place where to split...
        s = l
        e = l * 3 // 4
        if s > e and e > 2:
            for j in range(s, e, -1):
                if v[j] in  ' ])},;-+\n\t':
                    l = j
                    break
        F.write(v[:l]+cont+'\n')
        v = v[l:]
        pre = 0
    F.write(v + '\n')


def write_config(infofile, db, sdb=[], safe=True, rewrite_old = False,
                 split_long_lines=72, continuation_chars=None):
    """
    Write configuration data while preserving structure and inserting type modifiers.

    Parameters
    ----------
    infofile : str | bytes | Path | IO
        Destination path or open text stream; paths are created with mode 0o600.
    db : dict
        Mapping of keys (without '=' or '/') to Python values.
    sdb : list[tuple], optional
        Structure metadata from `read_config`; keeps ordering, comments, and blank lines.
    safe : bool
        Allow pickled `/p` and `/64p` payloads when False.
    rewrite_old : bool
        Re-emit keys that exist only in `sdb`.
    split_long_lines : int | None
        Maximum output width before `/C<char>` continuations are generated; falsy disables wrapping.
    continuation_chars : str | None
        Ordered list of glyphs to try for `/C<char>` markers; defaults to `funny_continuation_chars`.

    Notes
    -----
    - Values are encoded automatically (/r, /i, /f, /32, /64s, /64p, etc.).
    - `_write_split` chooses the first continuation character absent from the payload;
      if none remain the value is written unsplit and an error is logged.
    - Existing keys from `sdb` are emitted first, followed by any new keys in `db`.
    """
    if isinstance(infofile, (str, bytes, Path)): 
        with open(infofile,'w') as F:
            mychmod(infofile)
            write_config(
                F,
                db,
                sdb,
                safe,
                rewrite_old,
                split_long_lines,
                continuation_chars,
            )
        return
    if continuation_chars is None:
        continuation_chars = funny_continuation_chars
    assert isinstance(continuation_chars, str)
    #
    F = infofile
    #
    def write_k_v(k,v,F):
        def write_split(F, m, k, v):
            return _write_split(F, m, k, v, split_long_lines, continuation_chars)
        assert isinstance(k,str) and '=' not in k and '/' not in k
        if isinstance(v,str):
            if any( _is_ctrl(j) for j in v ):
                if any( _is_ctrl_but_rnc(j)  for j in v ):
                    # trigger on control chars not representable as '\t\r\n'
                    v = v.encode('utf8')
                    v = base64.b64encode(v)
                    v = v.decode()
                    write_split(F, '64s', k, v)
                else:
                    write_split(F, 'r', k, repr(v))
            else:
                write_split(F,'', k,v)
        elif isinstance(v, bool) or v is None:
            write_split(F, 'r', k, repr(v))
        elif isinstance(v,int):
            write_split(F, 'i', k, str(v))
        elif isinstance(v,float):
            write_split(F, 'f', k, repr(v))
        elif isinstance(v,bytes):
            write_split(F, '32', k, base64.b32encode(v).decode('ascii'))
        elif _check_eval_safe(v):
            write_split(F, 'r', k, repr(v))
            # will use ast.literal_eval for decoding
        elif not safe:
            write_split(F, '64p', k, base64.b64encode(pickle.dumps(v)).decode('ascii'))
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
    Read configuration data and capture structural metadata for future writes.

    Parameters
    ----------
    infofile : str | bytes | Path | Iterable[str]
        File path (opened automatically) or any iterable yielding text lines.
    safe : bool
        Allow `/p` and `/64p` unpickling when False; keep True for untrusted files.

    Returns
    -------
    tuple(dict, list)
        `(db, sdb)` where `db` maps keys to decoded Python values and `sdb`
        preserves layout as `(key, modifier, raw_line)` tuples (`None` for
        comments/blank lines, `False` for unparsable entries).

    Notes
    -----
    - Modifiers are applied left-to-right (`/64p` → base64 decode then unpickle).
    - Parsing continues after malformed lines, logging warnings so callers can react.
    """
    if isinstance(infofile, (str,bytes, Path)):
        with open(infofile) as F:
            db = _read_config(F, safe)
        return db
    return  _read_config(infofile, safe)

def _read_config(infofile, safe):
    """
    Core parser that produces `(db, sdb)` from an iterable of text lines.

    Parameters
    ----------
    infofile : Iterable[str]
        Already-open file or any line iterator.
    safe : bool
        Allow `/p` and `/64p` unpickling when False.

    Returns
    -------
    tuple(dict, list)
        See `read_config` for the meaning of `db` and `sdb`.

    Logs
    ----
    Emits warnings for malformed lines, unknown modifiers, or pickle attempts
    when `safe=True`.
    """
    def B(x): # to byte
        if isinstance(x, str):
            return x.encode('utf8')
        return x
    db = {}
    sdb = []
    I = iter(infofile)
    for line_ in I:
        line = line_.rstrip('\n\r')
        # skip comments and empty lines
        if not line.strip() or line.strip().startswith('#'):
            sdb.append( (None, None, line_) )
            continue
        if '=' not in line:
            logger.warning('In file %r ignored line %r', infofile, line)
            sdb.append( (False, False, line_) )
            continue
        m = key = value = False
        try:
            key,value = line.split('=',1)
            m=''
            if '/' in key:
                key,m = key.split('/',1)
            while m:
                if m.startswith('C'):
                    if len(m) < 2:
                        logger.warning('In file %r ignored line %r', infofile, line)
                        sdb.append( (False, False, line_) )
                        m = False
                        break
                    cont = m[1]
                    m = m[2:]
                    while value.endswith(cont):
                        l = next(I)
                        line_ += l
                        l = l.rstrip('\r\n')
                        value = value[:-1] + l
                elif m.startswith('p'):
                    if safe:
                        logger.error('In file %r cannot read %r, `safe` is True', infofile, line)
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
                        logger.warning('In file %r cannot convert to string the value : %r', infofile, value)
                    m = m[1:]
                elif m.startswith('b'):
                    if isinstance(value, str):
                        value = value.encode('utf8')
                    #elif isinstance(value, int):
                    #    value = value.to_bytes(....)
                    else:
                        logger.warning('In file %r cannot convert to bytes the value : %r', infofile, value)
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
                    logger.error('In file %r error parsing line modifiers : %r', infofile, line)
                    m = False
                    break
        #
        except Exception as E:
            logger.error('In file %r error parsing  %r : %r', infofile, line, E)
        if m == '' and key != False:
            db[key] = value
            sdb.append( (key, m, line_) )
        else:
            sdb.append( (False, False, line_) )
    return db, sdb  
