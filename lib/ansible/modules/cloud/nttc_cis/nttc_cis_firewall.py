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
module: nttc_cis_firewall
short_description: Create, Modify and Delete Firewall rules
description:
    - Create, Modify and Delete Firewall rules
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
            - The name of the Cloud Network Domain
        required: False
    network_domain:
        description:
            - The name of a Cloud Network Domain
        required: true
        default: None
    action:
        description:
            - The firewall rule action
        required: false
        default: ACCEPT_DECISIVELY
        choices: [ACCEPT_DECISIVELY, DENY]
    version:
        description:
            - The IP version
        required: false
        default: IPV4
        choices: [IPV4, IPv6]
    protocol:
        description:
            - The protocol
        required: false
        default: TCP
        choices: [TCP, UDP, IP, ICMP]
    src_ip:
        description:
            - The source IP address
        required: false
    src_ip_prefix:
        description:
            - The source IP prefix size
    src_ip_list:
        description:
            - The name of an existing IP address list
        required: false
    dst_ip:
        description:
            - The destination IP address
        required: false
    dst_ip_prefix:
        description:
            - The destination IP prefix size
    dst_ip_list:
        description:
            - The name of an existing IP address list
        required: false
    src_port_start:
        description:
            - The starting source port
            - omit all src port details for ANY
        required: false
    src_port_end:
        description:
            - The end of the port range
    src_port_list:
        description:
            - The name of an existing port list
        required: false
    dst_port_start:
        description:
            - The starting destination port
            - omit all dst port details for ANY
        required: false
    dst_port_end:
        description:
            - The end of the port range
    dst_port_list:
        description:
            - The name of an existing port list
        required: false
    enabled:
        description:
            - Whether to enable the firewall rule
        required: false
        default: true
        choices: [true, false]
    position:
        description:
            - Position of the firewall rule
            - If BEFORE or AFTER are used a position_to value is required
        required: false
        default: LAST
        choices: [FIRST, LAST, BEFORE, AFTER]
    position_to:
        description:
            - The name of an existing firewall rule to position the new rule
            - relative to
        required: false
    state:
        description:
            - The action to be performed
        required: true
        default: create
        choices: [list, get, create, update, delete]
notes:
    - N/A
'''

EXAMPLES = '''
# Create a firewall rule
- nttc_cis_firewall:
      region: na
      datacenter: NA9
      network_domain: "xxxx"
      name: "wwww"
      protocol: "UDP"
      version: "IPV6"
      src_ip_list: "yyyy"
      dst_ip_list: "zzzz"
      src_port_start: "ANY"
      dst_port_list: "my_port_list"
      enabled: True
      state: present
# Update a firewall rule
- nttc_cis_firewall:
      region: na
      datacenter: NA9
      network_domain: "xxxx"
      name: "wwww"
      protocol: "TCP"
      version: "IPV6"
      dst_ip_list: "zzzz"
      src_ip: "ffff:ffff:ffff:ffff::"
      src_ip_prefix: "64"
      src_port_start: "ANY"
      dst_port_list: "vvvv"
      enabled: True
      state: present
# Delete a firewall rule
- nttc_cis_firewall:
      region: na
      datacenter: NA9
      network_domain: "xxxx"
      name: "wwww"
      state: delete
'''

RETURN = '''
results:
    description: Dictonary of the firewall rule
    returned: state == present and wait == True
    type: complex
    contains:
        ipVersion:
            description: IP Version
            type: str
            sample: IPV6
        networkDomainId:
            description: The UUID of the Cloud Network Domain
            type: str
            sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
        protocol:
            description: The protocol for the firewall rule
            type: str
            sample: TCP
        name:
            description: The name of the firewall rule
            type: str
            sample: my_firewall_rule
        destination:
            description: The destination object for the rule, can be a single IP address or IP address list
            type: complex
            contains:
                ipAddressList:
                    description: The IP address list object
                    type: complex
                    contains:
                        id:
                            description: the UUID of the IP address list
                            type: str
                            sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
                        name:
                            description: The name of the IP address list
                            type: str
                            sample: my_ip_list
                portList:
                    description: The destination port list
                    type: complex
                    contains:
                        id:
                            description: The UUID of the port list
                            type: str
                            sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
                        name:
                            description: The name of the port list
                            type: str
                            sample: my port list
        enabled:
            description: The status of the firewall rule
            type: bool
        ruleType:
            description: Internal Use - is the rule internally or client created
            type: str
            sample: CLIENT_RULE
        datacenterId:
            description: Datacenter id/location
            type: str
            sample: NA9
        source:
            description: The source object for the rule, can be a single IP address or IP address list
            type: complex
            contains:
                ipAddressList:
                    description: The IP address list object
                    type: complex
                    contains:
                        id:
                            description: the UUID of the IP address list
                            type: str
                            sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
                        name:
                            description: The name of the IP address list
                            type: str
                            sample: my_ip_list
        state:
            description: Status of the VLAN
            type: str
            sample: NORMAL
        action:
            description: The rule action
            type: str
            sample: ACCEPT_DECISIVELY
        id:
            description: The UUID of the firewall rule
            type: str
            sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
'''

import traceback
from copy import deepcopy
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.nttc_cis.nttc_cis_utils import get_credentials, get_nttc_cis_regions, return_object, compare_json
from ansible.module_utils.nttc_cis.nttc_cis_provider import NTTCCISClient, NTTCCISAPIException


def create_fw_rule(module, client, network_domain_id):
    """
    Create a firewall rule

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :returns: The created firewall rule object
    """
    return_data = return_object('acl')
    args = module.params

    try:
        if args['src_ip_list'] is not None:
            args['src_ip_list'] = client.get_ip_list_by_name(network_domain_id, args['src_ip_list'], args['version'])['id']
        if args['dst_ip_list'] is not None:
            args['dst_ip_list'] = client.get_ip_list_by_name(network_domain_id, args['dst_ip_list'], args['version'])['id']
        if args['src_port_list'] is not None:
            args['src_port_list'] = client.get_port_list_by_name(network_domain_id, args['src_port_list'])['id']
        if args['dst_port_list'] is not None:
            args['dst_port_list'] = client.get_port_list_by_name(network_domain_id, args['dst_port_list'])['id']
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Could not determine IP address and port lists - {0}'.format(e.message), exception=traceback.format_exc())

    try:
        fw_rule = client.fw_args_to_dict(True, None, network_domain_id, args['name'],
                                         args['action'], args['version'],
                                         args['protocol'], args['src_ip'],
                                         args['src_ip_prefix'],
                                         args['src_ip_list'], args['dst_ip'],
                                         args['dst_ip_prefix'],
                                         args['dst_ip_list'],
                                         args['src_port_start'],
                                         args['src_port_end'],
                                         args['src_port_list'],
                                         args['dst_port_start'],
                                         args['dst_port_end'],
                                         args['dst_port_list'], args['enabled'],
                                         args['position'], args['position_to']
                                        )
        fw_rule_id = client.create_fw_rule(fw_rule)
        return_data['acl'] = client.get_fw_rule(network_domain_id, fw_rule_id)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not create the firewall rule - {0}'.format(e.message), exception=traceback.format_exc())
    except (KeyError, IndexError) as e:
        module.fail_json(changed=False, msg='Invalid data - {0}'.format(e.message), exception=traceback.format_exc())

    module.exit_json(changed=True, results=return_data['acl'])


def update_fw_rule(module, client, network_domain_id, existing_fw_rule):
    """
    Update a firewall rule

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg existing_fw_rule: The existing firewall rule to be updated
    :returns: The updated firewall rule object
    """
    return_data = return_object('acl')
    return_data['acl'] = {}
    args = module.params
    fw_rule_id = existing_fw_rule['id']

    # Build the parameter list to compare to the existing object in prepartion for update
    try:
        if args['src_ip_list'] is not None:
            args['src_ip_list'] = client.get_ip_list_by_name(network_domain_id, args['src_ip_list'], args['version'])['id']
        if args['dst_ip_list'] is not None:
            args['dst_ip_list'] = client.get_ip_list_by_name(network_domain_id, args['dst_ip_list'], args['version'])['id']
        if args['src_port_list'] is not None:
            args['src_port_list'] = client.get_port_list_by_name(network_domain_id, args['src_port_list'])['id']
        if args['dst_port_list'] is not None:
            args['dst_port_list'] = client.get_port_list_by_name(network_domain_id, args['dst_port_list'])['id']
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Could not determine IP address and port lists - {0}'.format(e.message), exception=traceback.format_exc())

    fw_rule = client.fw_args_to_dict(False, fw_rule_id, network_domain_id, args['name'], args['action'], args['version'],
                                     args['protocol'], args['src_ip'],
                                     args['src_ip_prefix'],
                                     args['src_ip_list'], args['dst_ip'],
                                     args['dst_ip_prefix'],
                                     args['dst_ip_list'],
                                     args['src_port_start'],
                                     args['src_port_end'],
                                     args['src_port_list'],
                                     args['dst_port_start'],
                                     args['dst_port_end'],
                                     args['dst_port_list'], args['enabled'],
                                     args['position'], args['position_to']
                                    )
    # Check for any state changes in the fw rule and update if required
    compare_result = compare_fw_rule(fw_rule, deepcopy(existing_fw_rule))
    if compare_result:
        try:
            if compare_result['changes']:
                client.update_fw_rule(fw_rule)
                return_data['acl'] = client.get_fw_rule_by_name(network_domain_id, args['name'])
                module.exit_json(changed=True, reuslts=return_data['acl'])
        except (KeyError, IndexError, NTTCCISAPIException) as e:
            module.fail_json(msg='Could not update the firewall rule - {0}'.format(e.message), exception=traceback.format_exc())
    module.exit_json(changed=False, results=existing_fw_rule)


def delete_fw_rule(module, client, network_domain_id, name):
    """
    Delete a firewall rule

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg name: The name of the firewall rule to be removed
    :returns: A message
    """
    try:
        fw_rule = client.get_fw_rule_by_name(network_domain_id, name)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not retrieve a list of firewall rules - {0}'.format(e.message), exception=traceback.format_exc())
    except KeyError:
        module.fail_json(msg='Network Domain is invalid')

    try:
        client.remove_fw_rule(fw_rule['id'])
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not delete the firewall rule - {0}'.format(e.message), exception=traceback.format_exc())
    except KeyError:
        module.fail_json(msg='Could not find the firewall rule - {0}'.format(e.message), exception=traceback.format_exc())

    module.exit_json(changed=True, msg='Firewall rule successfully removed')


def compare_fw_rule(new_fw_rule, existing_fw_rule):
    """
    Compare two firewall rules

    :arg new_fw_rule: The dict containing the specification for the new rule based on the supplied parameters
    :arg existing_fw_rule: The dict containing the speification for the existing firewall rule
    :returns: Any differences between the two firewall rules
    """
    existing_dst = existing_fw_rule['destination']
    existing_src = existing_fw_rule['source']
    existing_fw_rule['destination'] = {}
    existing_fw_rule['source'] = {}

    # Handle schema differences between the create/update schema and the returned get/list schema
    if 'ipAddressList' in existing_dst:
        existing_fw_rule['destination']['ipAddressListId'] = existing_dst['ipAddressList']['id']
    elif 'ip' in existing_dst:
        existing_fw_rule['destination']['ip'] = {}
        existing_fw_rule['destination']['ip']['address'] = existing_dst['ip']['address']
        if 'prefixSize' in existing_dst['ip']:
            existing_fw_rule['destination']['ip']['prefixSize'] = str(existing_dst['ip']['prefixSize'])
    if 'portList' in existing_dst:
        existing_fw_rule['destination']['portListId'] = existing_dst['portList']['id']
    elif 'port' in existing_dst:
        existing_fw_rule['destination']['port'] = {}
        existing_fw_rule['destination']['port']['begin'] = str(existing_dst['port']['begin'])
        if 'end' in existing_dst['port']:
            existing_fw_rule['destination']['port']['end'] = str(existing_dst['port']['end'])
    if 'ipAddressList' in existing_src:
        existing_fw_rule['source']['ipAddressListId'] = existing_src['ipAddressList']['id']
    elif 'ip' in existing_src:
        existing_fw_rule['source']['ip'] = {}
        existing_fw_rule['source']['ip']['address'] = existing_src['ip']['address']
        if 'prefixSize' in existing_src['ip']:
            existing_fw_rule['source']['ip']['prefixSize'] = str(existing_src['ip']['prefixSize'])
    if 'portList' in existing_src:
        existing_fw_rule['source']['portListId'] = existing_src['portList']['id']
    elif 'port' in existing_src:
        existing_fw_rule['source']['port'] = {}
        existing_fw_rule['source']['port']['begin'] = str(existing_src['port']['begin'])
        if 'end' in existing_src['port']:
            existing_fw_rule['source']['port']['end'] = str(existing_src['port']['end'])

    existing_fw_rule.pop('ruleType', None)
    existing_fw_rule.pop('datacenterId', None)
    existing_fw_rule.pop('state', None)
    existing_fw_rule.pop('ipVersion', None)
    existing_fw_rule.pop('name', None)
    existing_fw_rule.pop('networkDomainId', None)

    return compare_json(new_fw_rule, existing_fw_rule, None)


def main():
    """
    Main function

    :returns: Firewall rule Information
    """
    nttc_cis_regions = get_nttc_cis_regions()
    module = AnsibleModule(
        argument_spec=dict(
            region=dict(default='na', choices=nttc_cis_regions),
            datacenter=dict(required=True, type='str'),
            name=dict(required=False, type='str'),
            network_domain=dict(required=True, type='str'),
            action=dict(default='ACCEPT_DECISIVELY', choices=['ACCEPT_DECISIVELY', 'DENY']),
            version=dict(required=False, default='IPV4', choices=['IPV4', 'IPV6']),
            protocol=dict(default='TCP', choices=['TCP', 'UDP', 'IP', 'ICMP']),
            src_ip=dict(required=False, type='str'),
            src_ip_prefix=dict(required=False, type='str'),
            src_ip_list=dict(required=False, type='str'),
            dst_ip=dict(required=False, type='str'),
            dst_ip_prefix=dict(required=False, type='str'),
            dst_ip_list=dict(required=False, type='str'),
            src_port_start=dict(required=False, default=None, type='str'),
            src_port_end=dict(required=False, default=None, type='str'),
            src_port_list=dict(required=False, default=None, type='str'),
            dst_port_start=dict(required=False, default=None, type='str'),
            dst_port_end=dict(required=False, default=None, type='str'),
            dst_port_list=dict(required=False, default=None, type='str'),
            enabled=dict(default=True, type='bool'),
            position=dict(default='LAST', choices=['FIRST', 'LAST', 'BEFORE', 'AFTER']),
            position_to=dict(required=False, default=None, type='str'),
            state=dict(default='present', choices=['present', 'absent'])
        )
    )
    fw_rule_exists = None
    credentials = get_credentials()
    name = module.params['name']
    network_domain_name = module.params['network_domain']
    datacenter = module.params['datacenter']
    state = module.params['state']

    if credentials is False:
        module.fail_json(msg='Error: Could not load the user credentials')

    client = NTTCCISClient((credentials[0], credentials[1]), module.params.get('region'))

    # Get the CND object based on the supplied name
    try:
        network = client.get_network_domain_by_name(datacenter=datacenter, name=network_domain_name)
        network_domain_id = network.get('id')
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Failed to find the Cloud Network Domains - {0}'.format(e.message), exception=traceback.format_exc())

    # If a firewall rule name is provided try and locate the rule
    if name is not None:
        try:
            fw_rule_exists = client.get_fw_rule_by_name(network_domain_id, name)
        except NTTCCISAPIException as e:
            module.fail_json(msg='Could not locate the existing firewall rule - {0}'.format(e.message), exception=traceback.format_exc())

    try:
        if state == 'present':
            if fw_rule_exists is not None:
                update_fw_rule(module, client, network_domain_id, fw_rule_exists)
            else:
                create_fw_rule(module, client, network_domain_id)
        elif state == 'absent':
            if fw_rule_exists is not None:
                delete_fw_rule(module, client, network_domain_id, name)
            else:
                module.fail_json(msg='No rule found to delete')
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not operate on the firewall rule - {0}'.format(e.message), exception=traceback.format_exc())


if __name__ == '__main__':
    main()
