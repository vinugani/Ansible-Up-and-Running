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
module: nttc_cis_vip_pool
short_description: Create, update and delete VIP Pools
description:
    - Create, update and delete VIP Pools
    - It is quicker to use the option "id" to locate the VIP Pool if the UUID is known rather than search by name
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
          - Valid values can be found in nttcis.common.config.py under APIENDPOINTS
    datacenter:
        description:
            - The datacenter name
        required: true
        choices:
          - See NTTC CIS Cloud Web UI
    network_domain:
        description:
            - The name of a Cloud Network Domain
        required: true
        default: None
    id:
        description:
            - The UUID of the VIP Pool. Takes precendence over name
        required: false
    name:
        description:
            - The name of the VIP Pool
        required: false
    description:
        description:
            - The description for the VIP Pool
        required: false
    health_monitor_1:
        description:
            - The name of the procedure that the load balancer uses to verify that the Node is considered “healthy” and available for load balancing
            - A list of supported health monitors can be found here https://docs.mcp-services.net/x/5wMk
        required: false
    health_monitor_2:
        description:
            - The name of the procedure that the load balancer uses to verify that the Node is considered “healthy” and available for load balancing
            - This cannot be the same value as health_monitor_1
            - A list of supported health monitors can be found here https://docs.mcp-services.net/x/5wMk
        required: false
    no_health_monitor:
        description:
            - If True this will remove all health monitors from the VIP Pool
        required: false
        default: false
    load_balancing:
        description:
            - Defines how the Pool will handle load balancing
            - A list of supported load balancing methods can be found here https://docs.mcp-services.net/x/5wMk
        required: false
        default: "ROUND_ROBIN"
    service_down_action:
        description:
            - When a Pool Member fails to respond to a Health Monitor, the system marks that Pool Member down and removes any persistence entries associated with the Pool Member
            - The Action On Service Down feature specifies how the system should respond to already-established connections when the target Pool Member becomes unavailable.
        required: false
        default: None
    slow_ramp_time:
        description:
            - This allows a Server to slowly ramp up connections
            - The Slow Ramp Time feature (enabled by default) is used to slowly increase the number of connection requests that are load balanced to a new Pool Member.
            - The Slow Ramp Time setting controls the percentage of connections that are sent to a new Pool Member by specifying the duration (in seconds), that a Pool Member is in slow ramp mode
        required: false
        default: 10
    members:
        description:
            - A list of member objects for this VIP pool
        required: false
        suboptions:
            name:
                description:
                    - The name of the VIP Pool member
                required: true
            port:
                description:
                    - The TCP or UDP port to be used
                    - Specified as an integer
                required: true
    state:
        description:
            - The action to be performed
        default: present
        choices: [present, absent]

notes:
    - https://docs.mcp-services.net/x/5wMk
'''

EXAMPLES = '''
# Create a VIP Pool
- nttc_cis_vip_pool:
      region: na
      datacenter: NA9
      network_domain: "my_network_domain"
      name: "my_pool"
      description: "Test VIP Pool"
      health_monitor_1: "CCDEFAULT.Tcp"
      health_monitor_2: "CCDEFAULT.Http"
      members:
        - name: Node_01
          port: 443
        - name: Node_02
          port: 443
      state: present
# Update a specific VIP Pool
- nttc_cis_vip_pool:
      region: na
      datacenter: NA9
      network_domain: "my_network_domain"
      name: "my_pool"
      description: "Test VIP Pool"
      health_monitor_1: "CCDEFAULT.Tcp"
      health_monitor_2: "CCDEFAULT.Http"
      members:
        - name: Node_01
          port: 80
        - name: Node_02
          port: 443
          status: DISABLED
      state: present
# Delete a specific VIP Pool Member (To delete Node_02 from above, simply exclude it from the list of member objects)
- nttc_cis_vip_pool:
      region: na
      datacenter: NA9
      network_domain: "my_network_domain"
      name: "my_pool"
      members:
        - name: Node_01
          port: 80
      state: present
# Add a new VIP Pool Member (Node_03)
- nttc_cis_vip_pool:
      region: na
      datacenter: NA9
      network_domain: "my_network_domain"
      name: "my_pool"
      members:
        - name: Node_01
          port: 80
        - name: Node_03
          port: 80
      state: present
# Delete a specific VIP Pool
- nttc_cis_vip_pool_facts:
      region: na
      datacenter: NA9
      network_domain: "my_network_domain"
      name: "my_vip_pool"
      state: absent
'''

RETURN = '''
results:
    description: The UUID of the created or updated VIP Pool Object
    type: str
    returned: when state == present
    sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
msg:
    description: A useful message
    type: str
    returned: when state == absent
    sample: "The object was successfully deleted"
'''

from copy import deepcopy
from time import sleep
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.nttc_cis.nttc_cis_utils import get_credentials, get_nttc_cis_regions, compare_json
from ansible.module_utils.nttc_cis.nttc_cis_provider import NTTCCISClient, NTTCCISAPIException
from ansible.module_utils.nttc_cis.nttc_cis_config import VIP_NODE_STATES, LOAD_BALANCING_METHODS, VIP_POOL_SERVICE_DOWN_ACTIONS


def create_vip_pool(module, client, network_domain_id):
    """
    Create a VIP pool

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :returns: The created VIP pool dict
    """
    members = module.params.get('members')

    if not module.params.get('name'):
        module.fail_json(msg='A valid name is required')

    try:
        pool_result = client.create_vip_pool(network_domain_id, module.params.get('name'), module.params.get('description'),
                                             module.params.get('load_balancing'), module.params.get('service_down_action'),
                                             module.params.get('health_monitor'), module.params.get('slow_ramp_time'))
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Could not create the VIP Pool - {0}'.format(exc))

    try:
        if members:
            for member in members:
                client.add_vip_pool_member(pool_result, member.get('id'), member.get('port'), member.get('status'))
                # Introduce a pause in case the previous operation is still being processed and to stop the API getting smashed
                sleep(1)
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='The VIP Pool was created but there was a issue adding the members to the Pool. '
                             'Check the list of member objects - {0}'.format(exc))

    #return_data.get('vip_pool')['id'] = pool_result
    module.exit_json(changed=True, results=pool_result)


def update_vip_pool(module, client, pool):
    """
    Update a VIP pool

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg pool: The dict containing the existing pool to be updated
    :returns: The updated VIP pool UUID
    """
    try:
        pool_id = client.update_vip_pool(pool.get('id'), module.params.get('description'), module.params.get('load_balancing'),
                                         module.params.get('health_monitor'), module.params.get('no_health_monitor'),
                                         module.params.get('service_down_action'), module.params.get('slow_ramp_time'))
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Could not update the VIP Pool - {0}'.format(exc))

    # The next code block is not exactly stellar but is required to handle schema differences between objects/dicts
    # in order to be able to accurately compare two VIP pools and determine any differences
    if module.params.get('members'):
        try:
            updated_members = []
            removed_members = []
            added_members = []
            for existing_member in pool.get('members'):
                existing_member_found = False
                for new_member in module.params.get('members'):
                    if existing_member.get('node').get('id') == new_member.get('id'):
                        existing_member_tmp = {}
                        existing_member_tmp['id'] = existing_member.get('node').get('id')
                        existing_member_tmp['port'] = existing_member.get('port')
                        existing_member_tmp['status'] = existing_member.get('status')
                        compare_result = compare_json(new_member, existing_member_tmp, None)
                        if compare_result:
                            if compare_result['changes']:
                                # Save the actual pool member ID as it will be needed for the update
                                new_member['member_id'] = existing_member.get('id')
                                updated_members.append(new_member)
                        existing_member_found = True
                if not existing_member_found:
                    removed_members.append(existing_member)
            for new_member in module.params.get('members'):
                new_member_found = False
                for existing_member in pool.get('members'):
                    if new_member.get('id') == existing_member.get('node').get('id'):
                        new_member_found = True
                if not new_member_found:
                    added_members.append(new_member)

            # Make the member changes. Induce a 0.5sec pause to stop the API from being spammed on large member lists
            for member in removed_members:
                client.remove_vip_pool_member(member.get('id'))
                sleep(0.5)
            for member in added_members:
                client.add_vip_pool_member(pool_id, member.get('id'), member.get('port'), member.get('status'))
                sleep(0.5)
            for member in updated_members:
                client.remove_vip_pool_member(member.get('member_id'))
                sleep(0.5)
                client.add_vip_pool_member(pool_id, member.get('id'), member.get('port'), member.get('status'))
                sleep(0.5)

        except (KeyError, IndexError, NTTCCISAPIException) as exc:
            module.fail_json(msg='The VIP Pool was updated but there was a issue updating the members of the Pool. '
                             'Check the list of member objects - {0}'.format(exc)
                            )

    module.exit_json(changed=True, results=pool_id)


def delete_vip_pool(module, client, pool_id):
    """
    Delete a VIP pool

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg pool_id: The UUID of the existing VIP pool to be deleted
    :returns: A message
    """
    if pool_id is None:
        module.fail_json(msg='A value for id is required')
    try:
        client.remove_vip_pool(pool_id)
    except NTTCCISAPIException as exc:
        module.fail_json(msg='Could not delete the VIP Pool - {0}'.format(exc))

    module.exit_json(changed=True, msg='Successfully deleted the VIP Pool')


def verify_health_monitor(module, client, network_domain_id):
    """
    Verify the health monitor parameters provided are valid and will be accepted by Cloud Control

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the existing Cloud Network Domain
    :returns: The UUID (if any) of the Health Monitor profile in Cloud Control or None
    """
    hm_1_name = module.params.get('health_monitor_1')
    hm_2_name = module.params.get('health_monitor_2')
    hm_id = []

    try:
        health_monitors = client.list_vip_health_monitor(network_domain_id=network_domain_id)
        for profile in health_monitors:
            if hm_1_name == profile.get('name') and profile.get('poolCompatible'):
                hm_id.append(profile.get('id'))
            elif hm_2_name == profile.get('name') and profile.get('poolCompatible'):
                hm_id.append(profile.get('id'))
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Could not get a list of existing Health Monitoring profiles to check against - {0}'.format(exc))
    if hm_id:
        return hm_id

    return None

def verify_member_schema(module, client, network_domain_id):
    """
    Verify the VIP member parameters provided by the user to ensure Cloud Control will accept the configuration

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the existing Cloud Network Domain
    :returns: A list of of members (if any) or None
    """
    member_names = module.params.get('members')
    members = []

    if not isinstance(member_names, list):
        module.fail_json('The members argument must be a YAML list/array')
    # If the user has supplied more than 100 members, truncate to 100 as this is the maximum number of members in a VIP Pool
    elif len(member_names) > 100:
        del member_names[100:]
    try:
        nodes = client.list_vip_node(network_domain_id=network_domain_id)
        for member in member_names:
            if not isinstance(member, dict):
                module.fail_json('The members must be a YAML object/dictionary. Got {0}'.format(member))
            elif 'name' in member and 'port' in member:
                if member.get('name') is None or not isinstance(member.get('port'), int):
                    module.fail_json(msg='The member name cannot be None and the member port must be an integer')
                if member.get('port') < 1 or member.get('port') > 65535:
                    module.fail_json(msg='The member port must be in the range 1-65535')
                if member.get('status') in VIP_NODE_STATES:
                    status = member.get('status')
                else:
                    status = 'ENABLED'
                member_id = [x for x in nodes if x['name'] == member.get('name')][0].get('id')
                if member_id:
                    members.append({'id': member_id, 'port': member.get('port'), 'status': status})
            else:
                module.fail_json('Each member must contain a name and a port attribute. Got {0}'.format(member))
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Could not validate the schema of all of the member objects - {0}'.format(exc))
    if members:
        return members

    return None


def compare_vip_pool(module, pool):
    """
    Compare two VIP Pools

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg pool: The dict of the existing VIP pool to be compared to
    :returns: Any differences between the two VIP pools
    """
    new_pool = deepcopy(pool)
    existing_pool = deepcopy(pool)
    existing_health_monitors = []
    existing_members = None

    if module.params.get('description'):
        new_pool['description'] = module.params.get('description')
    if module.params.get('load_balancing'):
        new_pool['loadBalanceMethod'] = module.params.get('load_balancing')
    if module.params.get('service_down_action'):
        new_pool['serviceDownAction'] = module.params.get('service_down_action')
    if module.params.get('slow_ramp_time'):
        new_pool['slowRampTime'] = module.params.get('slow_ramp_time')
    if module.params.get('no_health_monitor'):
        new_pool['healthMonitorId'] = {'nil': True}
    elif module.params.get('health_monitor'):
        new_pool['healthMonitor'] = module.params.get('health_monitor')
        for profile in pool.get('healthMonitor'):
            existing_health_monitors.append(profile.get('id'))
        existing_pool['healthMonitor'] = existing_health_monitors

    if module.params.get('members'):
        existing_members = []
        for existing_member in existing_pool.get('members'):
            existing_member_tmp = {}
            existing_member_tmp['id'] = existing_member.get('node').get('id')
            existing_member_tmp['port'] = existing_member.get('port')
            existing_member_tmp['status'] = existing_member.get('status')
            existing_members.append(existing_member_tmp)
        existing_pool['members'] = existing_members
        new_pool['members'] = module.params.get('members')

    compare_result = compare_json(new_pool, existing_pool, None)
    return compare_result['changes']


def main():
    """
    Main function
    :returns: VIP Pool Information
    """
    nttc_cis_regions = get_nttc_cis_regions()
    module = AnsibleModule(
        argument_spec=dict(
            region=dict(default='na', choices=nttc_cis_regions),
            datacenter=dict(required=True, type='str'),
            network_domain=dict(required=True, type='str'),
            id=dict(default=None, required=False, type='str'),
            name=dict(default=None, required=False, type='str'),
            description=dict(required=False, default=None, type='str'),
            health_monitor_1=dict(required=False, default=None, type='str'),
            health_monitor_2=dict(required=False, default=None, type='str'),
            no_health_monitor=dict(required=False, default=False, type='bool'),
            load_balancing=dict(required=False, default='ROUND_ROBIN', choices=LOAD_BALANCING_METHODS),
            service_down_action=dict(required=False, default='NONE', choices=VIP_POOL_SERVICE_DOWN_ACTIONS),
            slow_ramp_time=dict(required=False, default=10, type='int'),
            members=dict(default=None, required=False, type='list'),
            state=dict(default='present', required=False, choices=['present', 'absent'])
        )
    )
    credentials = get_credentials()
    network_domain_name = module.params.get('network_domain')
    datacenter = module.params.get('datacenter')
    state = module.params.get('state')
    pool = None

    if credentials is False:
        module.fail_json(msg='Could not load the user credentials')

    client = NTTCCISClient((credentials[0], credentials[1]), module.params.get('region'))

    # Get the CND
    try:
        network = client.get_network_domain_by_name(name=network_domain_name, datacenter=datacenter)
        network_domain_id = network.get('id')
    except (KeyError, IndexError, NTTCCISAPIException):
        module.fail_json(msg='Could not find the Cloud Network Domain: {0}'.format(network_domain_name))


    # Verifying the supplied arguments
    if module.params.get('health_monitor_1') or module.params.get('health_monitor_2'):
        module.params['health_monitor'] = verify_health_monitor(module, client, network_domain_id)
    if module.params.get('members'):
        module.params['members'] = verify_member_schema(module, client, network_domain_id)

    # Check if the Pool already exists
    try:
        if module.params.get('id'):
            pool = client.get_vip_pool(module.params.get('id'))
        else:
            pools = client.list_vip_pool(network_domain_id=network_domain_id, name=module.params.get('name'))
            if len(pools) == 1:
                pool = pools[0]
        # Get the members of the pool if it exists
        try:
            if pool:
                pool['members'] = client.list_vip_pool_members(pool.get('id'))
        except (KeyError, IndexError, NTTCCISAPIException) as exc:
            module.fail_json(msg='{0}'.format(exc))
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Could not get a list of existing pools to check against - {0}'.format(exc))

    if state == 'present':
        if not pool:
            create_vip_pool(module, client, network_domain_id)
        if compare_vip_pool(module, pool):
            update_vip_pool(module, client, pool)
        module.exit_json(result=pool.get('id'))
    elif state == 'absent':
        if not pool:
            module.exit_json(msg='No VIP Pool not found. Nothing to remove.')
        delete_vip_pool(module, client, pool.get('id'))


if __name__ == '__main__':
    main()
