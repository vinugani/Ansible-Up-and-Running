#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2019 NTT Communications Cloud Infrastructure Services
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: nttc_cis_port_list
short_description: Create, update and delete Firewall Port Lists
description:
    - Create, update and delete Firewall Port Lists
version_added: 2.9
author:
    - Ken Sinfield (@kensinfield)
options:
    region:
        description:
            - The geographical region
        required: false
        default: na
        choices:
          - Valid values can be found in nttcis.common.config.py under
            APIENDPOINTS
    datacenter:
        description:
            - The datacenter name
        required: true
        choices:
          - See NTTC CIS Cloud Web UI
    name:
        description:
            - The name of the Port List
        required: true
    description:
        description:
            - The description of the Port List
        required: false
    network_domain:
        description:
            - The name of a Cloud Network Domain
        required: true
        default: None
    ports:
        description:
            - List of port groups with port_begin and optionally port_end
        required: false
    ports_nil:
        description:
            - Used on updating to remove all ports
        required: false
        choices: [true, false]
    child_port_lists:
        description:
            - List of port list names that will be included in this port list
        required: false
    child_port_list_nil:
        description:
            - Used on updating to remove all child port lists
        required: false
        choices: [true, false]
    state:
        description:
            - The action to be performed
        required: true
        default: present
        choices: [present, absent]
notes:
    - N/A
'''

EXAMPLES = '''
# Create a Port List
- nttc_cis_port_list:
      region: na
      datacenter: NA9
      network_domain: "xxxx"
      name: "APITEST"
      description: "API Testing"
      ports:
        - port_begin: 1077
        - port_begin: 1177
          port_end: 1277
      child_port_lists:
        - "APITEST_2"
      state: present
# Update a Port List
- nttc_cis_port_list:
      region: na
      datacenter: NA9
      network_domain: "xxxx"
      name: "APITEST"
      description: "API Testing 2"
      ports_nil: True
      child_port_lists:
        - "APITEST_3"
      state: present
# Delete a Port List
- nttc_cis_port_list:
      region: na
      datacenter: NA9
      network_domain: "xxxx"
      name: "APITEST"
      state: absent
'''

RETURN = '''
results:
    description: Array of Port List objects
    returned: success
    type: complex
    contains:
        id:
            description: Port List UUID
            type: str
            returned: when state == present
            sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
        description:
            description: Port List description
            type: str
            returned: when state == present
            sample: "My Port List description"
        name:
            description: Port List name
            type: str
            returned: when state == present
            sample: "My Port List"
        createTime:
            description: The creation date of the image
            type: str
            returned: when state == present
            sample: "2019-01-14T11:12:31.000Z"
        state:
            description: Status of the VLAN
            type: str
            returned: when state == present
            sample: NORMAL
        port:
            description: List of ports and/or port ranges
            type: complex
            returned: when state == present
            contains:
                begin:
                    description: The starting port number for this port or range
                    type: int
                    sample: 22
                end:
                    description: The end port number for this range. This is not present for single ports
                    type: int
                    sample: 23
        childPortList:
            description: List of child Port Lists
            type: complex
            returned: when state == present
            contains:
                id:
                    description: The ID of the Port List
                    type: str
                    sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
                name:
                    description: The name of the Port List
                    type: str
                    sample: "My Child Port List"
'''

import traceback
from copy import deepcopy
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.nttc_cis.nttc_cis_utils import get_credentials, get_nttc_cis_regions, return_object, compare_json
from ansible.module_utils.nttc_cis.nttc_cis_provider import NTTCCISClient, NTTCCISAPIException


def create_port_list(module, client, network_domain_id):
    """
    Create a port list

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :returns: The created port list object
    """
    return_data = return_object('port_list')
    name = module.params.get('name')
    description = module.params.get('description')
    ports = module.params.get('ports')
    child_port_lists = module.params.get('child_port_lists')
    if name is None:
        module.fail_json(msg='A valid name is required')
    if not ports == 0 and not child_port_lists:
        module.fail_json(msg='ports or child_ports_list must have at least one valid entry')
    try:
        client.create_port_list(network_domain_id, name, description, ports, child_port_lists)
        return_data['port_list'] = client.get_port_list_by_name(network_domain_id, name)
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Could not create the Port List {0}'.format(e))

    module.exit_json(changed=True, results=return_data.get('port_list'))


def update_port_list(module, client, network_domain_id, port_list):
    """
    Update a port list

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg port_list: The dict containing the existing port list to be updated
    :returns: The updated port list dict
    """
    return_data = return_object('port_list')
    name = module.params.get('name')

    try:
        client.update_port_list(network_domain_id,
                                port_list.get('id'),
                                module.params.get('description'),
                                module.params.get('ports'),
                                module.params.get('ports_nil'),
                                module.params.get('child_port_lists'),
                                module.params.get('child_port_lists_nil')
                               )
        return_data['port_list'] = client.get_port_list_by_name(network_domain_id, name)
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Could not update the Port List - {0}'.format(e))

    module.exit_json(changed=True, results=return_data['port_list'])


def compare_port_list(module, client, network_domain_id, port_list):
    """
    Compare two port lists

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of a Cloud Network Domain
    :arg port_list: The dict of the existing port list to be compared to
    :returns: Any differences between the two port lists
    """
    # Handle schema differences between the returned API object and the one required to be sent
    child_port_list_ids = []
    for i in range(len(port_list['childPortList'])):
        child_port_list_ids.append(port_list['childPortList'][i].get('id'))
    port_list.pop('childPortList')
    port_list['childPortListId'] = child_port_list_ids
    port_list.pop('state')
    port_list.pop('createTime')
    new_port_list = client.port_list_args_to_dict(False,
                                                  network_domain_id,
                                                  port_list.get('id'),
                                                  port_list.get('name'),
                                                  module.params.get('description'),
                                                  module.params.get('ports'),
                                                  module.params.get('ports_nil'),
                                                  module.params.get('child_port_lists'),
                                                  module.params.get('child_port_lists_nil')
                                                 )
    if module.params.get('child_port_lists_nil') and not port_list.get('childPortListId'):
        new_port_list['childPortListId'] = []
    if module.params.get('ports_nil') and not port_list.get('ports'):
        new_port_list['ports'] = []
    compare_result = compare_json(new_port_list, port_list, None)
    return compare_result.get('changes')


def delete_port_list(module, client, port_list):
    """
    Delete a port lists

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg port_list: The dict of the existing port list to be deleted
    :returns: A message
    """
    try:
        client.remove_port_list(port_list.get('id'))
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not delete the Port List - {0}'.format(e.message), exception=traceback.format_exc())

    module.exit_json(changed=True)


def main():
    """
    Main function

    :returns: Port list Information
    """
    nttc_cis_regions = get_nttc_cis_regions()
    module = AnsibleModule(
        argument_spec=dict(
            region=dict(default='na', choices=nttc_cis_regions),
            datacenter=dict(required=True, type='str'),
            name=dict(required=True, type='str'),
            description=dict(required=False, type='str'),
            ports=dict(required=False, type='list'),
            ports_nil=dict(required=False, default=False, type='bool'),
            child_port_lists=dict(required=False, type='list'),
            child_port_lists_nil=dict(required=False, default=False, type='bool'),
            network_domain=dict(required=True, type='str'),
            state=dict(default='present', choices=['present', 'absent'])
        )
    )
    credentials = get_credentials()
    name = module.params.get('name')
    network_domain_name = module.params.get('network_domain')
    datacenter = module.params.get('datacenter')
    state = module.params.get('state')

    if credentials is False:
        module.fail_json(msg='Error: Could not load the user credentials')

    client = NTTCCISClient((credentials[0], credentials[1]), module.params.get('region'))

    # Get a list of existing CNDs and check if the name already exists
    try:
        network = client.get_network_domain_by_name(name=network_domain_name, datacenter=datacenter)
        network_domain_id = network.get('id')
    except NTTCCISAPIException as e:
        module.fail_json(msg='Failed to get a list of Cloud Network Domains - {0}'.format(e.message), exception=traceback.format_exc())
    if not network:
        module.fail_json(msg='Failed to find the Cloud Network Domain Check the network_domain value')

    # Get a list of existing VLANs and check if the new name already exists
    try:
        port_list = client.get_port_list_by_name(name=name, network_domain_id=network_domain_id)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Failed to get a list of Port Lists - {0}'.format(e.message), exception=traceback.format_exc())

    if state == 'present':
        if not port_list:
            create_port_list(module, client, network_domain_id)
        else:
            if compare_port_list(module, client, network_domain_id, deepcopy(port_list)):
                update_port_list(module, client, network_domain_id, port_list)
            module.exit_json(result=port_list)
    elif state == 'absent':
        if not port_list:
            module.exit_json(msg='Port List {0} was not found'.format(name))
        delete_port_list(module, client, port_list)


if __name__ == '__main__':
    main()
