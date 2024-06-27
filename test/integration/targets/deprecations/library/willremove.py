# -*- coding: utf-8 -*-
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = r'''
---
module: willremove
version_added: histerical
short_description: does nothing
description: does nothing, this is deprecation test
deprecated:
    removed_in: '3.30'
    why: cause i wanna!
    alternatives: no soup for you!
options:
  one:
    description:
    - first option
    type: bool
    default: no
  two:
    description:
    - second option
notes:
- Just noop to test module deprecation
seealso:
- module: removeoption
author:
- Ansible Core Team
attributes:
    action:
      support: full
    async:
      support: full
    bypass_host_loop:
      support: none
    check_mode:
      support: full
    diff_mode:
      support: none
    platform:
      platforms: all
'''

EXAMPLES = r'''
- name: useless
  willremove:
    one: true
    two: /etc/file.conf
'''

RETURN = r'''
'''

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            one=dict(type='bool', default='no'),
            two=dict(type='str'),
        ),
        supports_check_mode=True
    )

    one = module.params['one']
    two = module.params['two']

    result = {'yolo': 'lola'}

    module.exit_json(**result)


if __name__ == '__main__':
    main()
