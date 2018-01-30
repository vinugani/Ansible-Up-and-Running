#!/usr/bin/env python

# a script to check for illegal filenames on various Operating Systems. The
# main rules are derived from restrictions on Windows
# https://msdn.microsoft.com/en-us/library/aa365247#naming_conventions

import os
import re
import struct

from ansible.module_utils.basic import to_bytes

ILLEGAL_CHARS = [
    b'<',
    b'>',
    b':',
    b'"',
    b'/',
    b'\\',
    b'|',
    b'?',
    b'*'
] + [struct.pack("b", i) for i in range(32)]

ILLEGAL_NAMES = [
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
]

ILLEGAL_END_CHARS = [
    '.',
    ' ',
]


def check_path(path, dir=False):
    errors = []
    type_name = 'directory' if dir else 'file'
    parent, file_name = os.path.split(path)
    name, ext = os.path.splitext(file_name)

    if name.upper() in ILLEGAL_NAMES:
        errors.append("Illegal %s name %s: %s" % (type_name, name.upper(), path))

    if file_name[-1] in ILLEGAL_END_CHARS:
        errors.append("Illegal %s name end-char '%s': %s" % (type_name, file_name[-1], path))

    bfile = to_bytes(file_name, encoding='utf-8')
    for char in ILLEGAL_CHARS:
        if char in bfile:
            bpath = to_bytes(path, encoding='utf-8')
            errors.append("Illegal char %s in %s name: %s" % (char, type_name, bpath))
    return errors


def main():
    errors = []
    pattern = re.compile("^./test/integration/targets/.*/backup")

    for root, dirs, files in os.walk('.'):
        # ignore test/integration/targets/*/backup
        if pattern.match(root):
            continue

        for dir_name in dirs:
            errors += check_path(os.path.abspath(os.path.join(root, dir_name)), dir=True)

        for file_name in files:
            errors += check_path(os.path.abspath(os.path.join(root, file_name)), dir=False)

    if len(errors) > 0:
        print('Ansible git repo should not contain any illegal filenames')
        for error in errors:
            print(error)
        exit(1)


if __name__ == '__main__':
    main()
