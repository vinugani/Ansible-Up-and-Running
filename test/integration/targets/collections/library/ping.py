#!/usr/bin/env python

import json


def main():
    print(json.dumps(dict(changed=False, source='legacy_library_dir')))


if __name__ == '__main__':
    main()
