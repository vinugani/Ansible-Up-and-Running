"""Check shebangs, execute bits and byte order marks."""
from __future__ import annotations

import os
import re
import stat
import sys


standard_shebangs = set([
    b'#!/bin/bash -eu',
    b'#!/bin/bash -eux',
    b'#!/bin/sh',
    b'#!/usr/bin/env bash',
    b'#!/usr/bin/env fish',
    b'#!/usr/bin/env pwsh',
    b'#!/usr/bin/env python',
    b'#!/usr/bin/make -f',
])

integration_shebangs = set([
    b'#!/bin/sh',
    b'#!/usr/bin/env bash',
    b'#!/usr/bin/env python',
])

module_shebangs = {
    '': b'#!/usr/bin/python',
    '.py': b'#!/usr/bin/python',
    '.ps1': b'#!powershell',
}

# see https://unicode.org/faq/utf_bom.html#bom1
byte_order_marks = (
    (b'\x00\x00\xFE\xFF', 'UTF-32 (BE)'),
    (b'\xFF\xFE\x00\x00', 'UTF-32 (LE)'),
    (b'\xFE\xFF', 'UTF-16 (BE)'),
    (b'\xFF\xFE', 'UTF-16 (LE)'),
    (b'\xEF\xBB\xBF', 'UTF-8'),
)


def is_excluded_path(path):
    """
    Determine if a path should be skipped from this sanity test.
    Usually because it is not for use by Ansible, like files in roles/files.
    """
    if path.startswith('examples/'):
        # examples trigger some false positives due to location
        return True
    if re.search('roles/[^/]+/files/', path) or re.search('roles/[^/]+/templates/', path):
        # Ansible doesn't need to verify the data files and templates of roles
        # see https://github.com/ansible/ansible/issues/76612
        return True
    return False


def validate_shebang(shebang, mode, path):
    if is_excluded_path(path):
        return True

    executable = (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) & mode

    if not shebang or not shebang.startswith(b'#!'):
        if executable:
            print('%s:%d:%d: file without shebang should not be executable' % (path, 0, 0))
            return False

        for mark, name in byte_order_marks:
            if shebang.startswith(mark):
                print('%s:%d:%d: file starts with a %s byte order mark' % (path, 0, 0, name))
                return False
        return True

    is_module = False
    is_integration = False

    dirname = os.path.dirname(path)

    if path.startswith('lib/ansible/modules/'):
        is_module = True
    elif re.search('^test/support/[^/]+/plugins/modules/', path):
        is_module = True
    elif re.search('^test/support/[^/]+/collections/ansible_collections/[^/]+/[^/]+/plugins/modules/', path):
        is_module = True
    elif path == 'test/lib/ansible_test/_util/target/cli/ansible_test_cli_stub.py':
        pass  # ansible-test entry point must be executable and have a shebang
    elif re.search(r'^lib/ansible/cli/[^/]+\.py', path):
        pass  # cli entry points must be executable and have a shebang
    elif path.startswith('lib/') or path.startswith('test/lib/'):
        if executable:
            print('%s:%d:%d: should not be executable' % (path, 0, 0))
            return False

        if shebang:
            print('%s:%d:%d: should not have a shebang' % (path, 0, 0))
            return False
        return True
    elif path.startswith('test/integration/targets/') or path.startswith('tests/integration/targets/'):
        is_integration = True

        if dirname.endswith('/library') or '/plugins/modules' in dirname or dirname in (
                # non-standard module library directories
                'test/integration/targets/module_precedence/lib_no_extension',
                'test/integration/targets/module_precedence/lib_with_extension',
        ):
            is_module = True
    elif path.startswith('plugins/modules/'):
        is_module = True

    if is_module:
        if executable:
            print('%s:%d:%d: module should not be executable' % (path, 0, 0))

        ext = os.path.splitext(path)[1]
        expected_shebang = module_shebangs.get(ext)
        expected_ext = ' or '.join(['"%s"' % k for k in module_shebangs])

        if expected_shebang:
            if shebang == expected_shebang:
                return True

            print('%s:%d:%d: expected module shebang "%s" but found: %s' % (path, 1, 1, expected_shebang, shebang))
            return False
        else:
            print('%s:%d:%d: expected module extension %s but found: %s' % (path, 0, 0, expected_ext, ext))
            return False
    else:
        if is_integration:
            allowed = integration_shebangs
        else:
            allowed = standard_shebangs

        if shebang not in allowed:
            print('%s:%d:%d: unexpected non-module shebang: %s' % (path, 1, 1, shebang))
            return False
    return True


def main():
    for path in sys.argv[1:] or sys.stdin.read().splitlines():
        with open(path, 'rb') as path_fd:
            shebang = path_fd.readline().strip()
            mode = os.stat(path).st_mode

            validate_shebang(shebang, mode, path)


if __name__ == '__main__':
    main()
