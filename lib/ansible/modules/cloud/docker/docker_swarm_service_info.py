#!/usr/bin/python
#
# (c) 2019 Hannes Ljungberg <hannes.ljungberg@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: docker_swarm_service_info

short_description: Retrieves information about docker services from a Swarm Manager

description:
  - Retrieves information about a docker service.
  - Essentially returns the output of C(docker service inspect <name>).
  - Must be executed on a host running as Swarm Manager, otherwise the module will fail.

version_added: "2.8"

options:
  name:
    description:
      - The name of the service to inspect.
    type: str
extends_documentation_fragment:
  - docker
  - docker.docker_py_1_documentation

author:
  - Hannes Ljungberg (@hannseman)

requirements:
  - "L(Docker SDK for Python,https://docker-py.readthedocs.io/en/stable/) >= 2.0.0"
  - "Docker API >= 1.24"
'''

EXAMPLES = '''
- name: Get info from a service
  docker_swarm_service_info:
    name: myservice
  register: result
'''

RETURN = '''
exists:
    description:
      - Returns whether the service exists.
    type: bool
    returned: always
    sample: true
service:
    description:
      - A dictionary representing the current state of the service. Matches the C(docker service inspect) output.
      - Will be C(None) if service does not exist.
    returned: always
    type: dict
'''

from ansible.module_utils.docker.swarm import AnsibleDockerSwarmClient


def get_service_info(client):
    service = client.module.params['name']
    return client.get_service_inspect(
        service_id=service,
        skip_missing=True
    )


def main():
    argument_spec = dict(
        name=dict(type='str'),
    )

    client = AnsibleDockerSwarmClient(
        argument_spec=argument_spec,
        supports_check_mode=True,
        min_docker_version='2.0.0',
        min_docker_api_version='1.24',
    )

    client.fail_task_if_not_swarm_manager()

    service = get_service_info(client)

    client.module.exit_json(
        changed=False,
        service=service,
        exists=bool(service)
    )


if __name__ == '__main__':
    main()
