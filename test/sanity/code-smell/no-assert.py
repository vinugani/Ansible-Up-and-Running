#!/usr/bin/env python
from __future__ import print_function

import os
import re
import sys

ASSERT_RE = re.compile(br'^\s*assert[^a-z0-9_:]')


def main():
    skip = set([
        'test/sanity/code-smell/%s' % os.path.basename(__file__),
        'lib/ansible/module_utils/compat/ipaddress.py',
        'lib/ansible/module_utils/distro/_distro.py',
    ])

    for path in sys.argv[1:] or sys.stdin.read().splitlines():
        if path in skip:
            continue

        with open(path, 'rb') as f:
            for i, line in enumerate(f.readlines()):
                matches = ASSERT_RE.findall(line)

                if matches:
                    lineno = i + 1
                    colno = line.index(b'assert') + 1
                    if sys.version_info[0] == 3:
                        match = matches[0].decode('utf-8')
                    else:
                        match = matches[0]
                    print('%s:%d:%d: raise AssertionError instead of: %s' % (path, lineno, colno, match[colno - 1:]))


if __name__ == '__main__':
    main()
