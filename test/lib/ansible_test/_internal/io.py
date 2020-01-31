"""Functions for disk IO."""
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import errno
import json
import os

from . import types as t

from .encoding import (
    ENCODING,
)

from .util import (
    to_bytes,
    to_text,
)


def read_json_file(path):  # type: (t.AnyStr) -> t.Any
    """Parse and return the json content from the specified path."""
    return json.loads(read_text_file(path))


def read_text_file(path):  # type: (t.AnyStr) -> t.Text
    """Return the contents of the specified path as text."""
    return to_text(read_binary_file(path))


def read_binary_file(path):  # type: (t.AnyStr) -> bytes
    """Return the contents of the specified path as bytes."""
    with open_binary_file(path) as file:
        return file.read()


def make_dirs(path):  # type: (str) -> None
    """Create a directory at path, including any necessary parent directories."""
    try:
        os.makedirs(to_bytes(path))
    except OSError as ex:
        if ex.errno != errno.EEXIST:
            raise


def write_json_file(path, content, create_directories=False, formatted=True):  # type: (str, t.Union[t.List[t.Any], t.Dict[str, t.Any]], bool, bool) -> None
    """Write the given json content to the specified path, optionally creating missing directories."""
    text_content = json.dumps(content, sort_keys=formatted, indent=4 if formatted else None, separators=(', ', ': ') if formatted else (',', ':')) + '\n'
    write_text_file(path, text_content, create_directories=create_directories)


def write_text_file(path, content, create_directories=False):  # type: (str, str, bool) -> None
    """Write the given text content to the specified path, optionally creating missing directories."""
    if create_directories:
        make_dirs(os.path.dirname(path))

    with open_binary_file(path, 'wb') as file:
        file.write(to_bytes(content))


def open_text_file(path, mode='r'):  # type: (str, str) -> t.TextIO
    """Open the given path for text access."""
    if 'b' in mode:
        raise Exception('mode cannot include "b" for text files: %s' % mode)

    # noinspection PyTypeChecker
    return open(to_bytes(path), mode, encoding=ENCODING)


def open_binary_file(path, mode='rb'):  # type: (str, str) -> t.BinaryIO
    """Open the given path for binary access."""
    if 'b' not in mode:
        raise Exception('mode must include "b" for binary files: %s' % mode)

    # noinspection PyTypeChecker
    return open(to_bytes(path), mode)
