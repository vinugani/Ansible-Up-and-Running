#!/usr/bin/python
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = """
---
module: checkpoint_install_policy
short_description: Install policy on Checkpoint devices over Web Services API
description:
  - Install policy on Checkpoint devices.
    All operations are performed over Web Services API.
version_added: "2.9"
author: "Or Soffer (@chkp-orso)"
options:
  policy_package:
    description:
      - The name of the Policy Package to be installed.
    type: str
    required: True
  targets:
    description:
      - On what targets to execute this command. Targets may be identified by their name, or object unique identifier.
    type: list
    required: True
  access:
    description:
      - Set to be true in order to install the Access Control policy. By default, the value is true if Access Control
        policy is enabled on the input policy package, otherwise false.
    type: bool
  desktop_security:
    description:
      - Set to be true in order to install the Desktop Security policy. By default, the value is true if desktop
        security policy is enabled on the input policy package, otherwise false.
    type: bool
  qos:
    description:
      - Set to be true in order to install the QoS policy. By default, the value is true if Quality-of-Service policy is
        enabled on the input policy package, otherwise false.
    type: bool
  threat_prevention:
    description:
      - Set to be true in order to install the Threat Prevention policy. By default, the value is true if Threat
        Prevention policy is enabled on the input policy package, otherwise false.
    type: bool
  install_on_all_cluster_members_or_fail:
    description:
      - Relevant for the gateway clusters. If true, the policy is installed on all the cluster members. If the
        installation on a cluster member fails, don't install on that cluster.
    type: bool
  prepare_only:
    description:
      - If true, prepares the policy for the installation, but doesn't install it on an installation target.
    type: bool
  revision:
    description:
      - The UID of the revision of the policy to install.
    type: str
"""

EXAMPLES = """
- name: Install policy
  checkpoint_install_policy:
    policy_package: "standard"
    targets: "the_target"
"""

RETURN = """
checkpoint_install_policy:
  description: The checkpoint install policy output.
  returned: always.
  type: str
"""


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.checkpoint.checkpoint import api_command


def main():
    argument_spec = dict(
        policy_package=dict(type='str', required=True),
        targets=dict(type='list', required=True),
        access=dict(type='bool'),
        desktop_security=dict(type='bool'),
        qos=dict(type='bool'),
        threat_prevention=dict(type='bool'),
        install_on_all_cluster_members_or_fail=dict(type='bool'),
        prepare_only=dict(type='bool'),
        revision=dict(type='str')
    )

    user_parameters = list(argument_spec.keys())
    module = AnsibleModule(argument_spec=argument_spec)
    command = "install-policy"

    api_command(module, command, user_parameters)


if __name__ == '__main__':
    main()
