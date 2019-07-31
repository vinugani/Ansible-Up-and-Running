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
module: nttc_cis_connectivity
short_description: List, Create and Destory an Ansible Bastion Host
description:
    - List, Create and Destory an Ansible Bastion Host
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
    vlan:
        description:
            - The name of the VLAN to create the Bastion Host in
        required: true
    name:
        description:
            - The name of the Bastion Host
        required: false
        default: ansible_gw
    password:
        description:
            - The root password for the host
        required: false
        default: None
    ipv4:
        description:
            - The IPv4 address of the host
            - If one is not provided one will be automatically allocated
        required: false
        default: None
    src_ip:
        description:
            - The IPv4 source network/host address to restrict SSH access to the Bastion Host public IPv4 address
        required: false
        default: ANY
    src_prefix:
        description:
            - The IPv4 subnet mask to apply to the src_ip address
        required: false
        default: None
    wait:
        description:
            - Wait for the server to complete deployment
        required: false
        default: true
    wait_time:
            description:
                - The maximum time the module will wait for the server to complete deployment in seconds
            required: false
            default: 600
    wait_poll_time:
            description:
                - How often the module will poll the Cloud Control API to check the status of the Bastion Host deployment in seconds
            required: false
            default: 30
    state:
        description:
            - The action to be performed
        default: present
        choices: [present, absent]

notes:
'''
EXAMPLES = '''
# Create a Bastion Host with minimal settings
- nttc_cis_connectivity:
      region: na
      datacenter: NA9
      network_domain: "my_network_domain"
      vlan: "my_vlan"
      state: present
# Create a Bastion Host
- nttc_cis_connectivity:
      region: na
      datacenter: NA9
      network_domain: "my_network_domain"
      vlan: "my_vlan"
      name: "my_gateway_host"
      password: "my_passwrd"
      src_ip: x.x.x.x
      src_prefix: 32
      state: present
'''
RETURN = '''
results:
    description: Object with the Bastion Host details
    type: complex
    returned: when state == present
    contains:
        id:
            description: The UUID of the server
            type: str
            sample: "b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae"
        password:
            description: The password for the server if generated by the module
            type: str
            sample: "my_password"
        private_ipv4:
            description: The private IPv4 address of the Bastion Host
            type: str
            sample: "10.0.0.10"
        ipv6:
            description: The IPv6 address of the Bastion Host
            type: str
            sample: "1111:1111:1111:1111:0:0:0:1"
        public_ipv4:
            description: The public IPv4 address assigned to the Bastion Host
            type: str
            sample: "x.x.x.x"
'''


import traceback
from time import sleep
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.nttc_cis.nttc_cis_utils import get_credentials, get_nttc_cis_regions, generate_password
from ansible.module_utils.nttc_cis.nttc_cis_provider import NTTCCISClient, NTTCCISAPIException

ACL_RULE_NAME = 'Ipv4.Internet.to.Ansible.SSH'


def create_server(module, client, network_domain_id, vlan_id):
    """
    Create the Bastion Host

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain for the Bastion Host
    :arg vlan_id: The UUID of the VLAN for the Bastion Host
    :returns: The Bastion Host server object
    """
    params = {}
    params['networkInfo'] = {}
    params['networkInfo']['primaryNic'] = {}
    datacenter = module.params['datacenter']

    params['networkInfo']['networkDomainId'] = network_domain_id
    params['networkInfo']['primaryNic']['vlanId'] = vlan_id
    if module.params['ipv4'] is not None:
        params['networkInfo']['primaryNic']['privateIpv4'] = module.params['ipv4']

    params['imageId'] = 'a51a1500-e7d5-4453-9591-8115b1c48202'
    params['name'] = module.params['name']
    params['start'] = True
    ngoc = False

    if module.params['password'] is not None:
        params['administratorPassword'] = module.params['password']
    else:
        params['administratorPassword'] = generate_password()

    try:
        client.create_server(ngoc, params)
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Could not create the server - {0}'.format(exc.message), exception=traceback.format_exc())

    wait_result = wait_for_server(module, client, params['name'], datacenter, network_domain_id, 'NORMAL', True, False, None)
    if wait_result is None:
        module.fail_json(msg='Could not verify the server creation. Password: {0}'.format(params['administratorPassword']))

    wait_result['password'] = params['administratorPassword']
    return wait_result


def allocate_public_ip(module, client, network_domain_id):
    """
    Allocate the Public IP to the Bastion Host

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain for the Bastion Host
    """
    return_data = {}
    try:
        return_data['id'] = client.add_public_ipv4(network_domain_id)
        return_data['ip'] = client.get_public_ipv4(return_data['id'])['baseIp']
        return return_data
    except NTTCCISAPIException as exc:
        module.fail_json(msg='Could not add a public IPv4 block - {0}'.format(exc.message), exception=traceback.format_exc())
    except KeyError:
        module.fail_json(msg='Network Domain is invalid or an API failure occurred.')


def create_nat_rule(module, client, network_domain_id, internal_ip, external_ip):
    """
    Create the NAT rule for the Bastion Host

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain for the Bastion Host
    :arg internal_ip: The private IPv4 address of the Bastion Host
    :arg external_ip: The public IPv4 address to use
    """
    if internal_ip is None or external_ip is None:
        module.fail_json(msg='Valid internal_ip and external_ip values are required')
    try:
        return client.create_nat_rule(network_domain_id, internal_ip, external_ip)
    except NTTCCISAPIException as exc:
        module.fail_json(msg='Could not create the NAT rule - {0}'.format(exc.message), exception=traceback.format_exc())
    except KeyError:
        module.fail_json(msg='Network Domain is invalid')


def create_fw_rule(module, client, network_domain_id, public_ipv4):
    """
    Create the firewall rule for the Bastion Host

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain for the Bastion Host
    :arg public_ipv4: The public IPv4 address to use
    """
    src_ip = module.params['src_ip']
    src_prefix = module.params['src_prefix']
    try:
        return client.create_fw_rule(network_domain_id,
                                     ACL_RULE_NAME,
                                     'ACCEPT_DECISIVELY',
                                     'IPV4',
                                     'TCP',
                                     src_ip,
                                     src_prefix,
                                     None,
                                     public_ipv4,
                                     None,
                                     None,
                                     'ANY',
                                     None,
                                     None,
                                     '22',
                                     None,
                                     None,
                                     True,
                                     'FIRST',
                                     None)
    except NTTCCISAPIException as exc:
        module.fail_json(msg='Could not create the firewall rule - {0}'.format(exc.message), exception=traceback.format_exc())


def update_fw_rule(module, client, fw_rule, public_ipv4):
    """
    Update the firewall rule for the Bastion Host

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg fw_rule: The existing firewall rule
    :arg public_ipv4: The public IPv4 address to use
    """
    fw_rule_id = fw_rule.get('id')
    src_ip = module.params.get('src_ip')
    src_prefix = module.params.get('src_prefix')

    try:
        client.update_fw_rule(fw_rule_id, 'ACCEPT_DECISIVELY', 'TCP', src_ip, src_prefix, None, public_ipv4, None, None,
                              'ANY', None, None, '22', None, None, True, 'FIRST', None)
    except NTTCCISAPIException as exc:
        module.fail_json(msg='Could not update the firewall rule - {0}'.format(exc.message), exception=traceback.format_exc())
    except KeyError as exc:
        module.fail_json(changed=False, msg='Invalid data - {0}'.format(exc.message), exception=traceback.format_exc())


def wait_for_server(module, client, name, datacenter, network_domain_id, state, check_for_start=False,
                    check_for_stop=False, wait_poll_interval=None):
    """
    Wait for the server deployment to complete.

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg datacenter: The MCP ID
    :arg network_domain_id: The UUID of the network domain for the Bastion Host
    :arg state: The state to wait for e.g. NORMAL
    :arg check_for_start: Should we check if the server is started
    :arg check_for_stop: Should we check if the server is stooped
    :arg wait_poll_internal: Optional custom wait polling interval value in seconds
    """
    set_state = False
    actual_state = ''
    start_state = ''
    time = 0
    wait_time = module.params['wait_time']
    if wait_poll_interval is None:
        wait_poll_interval = module.params['wait_poll_interval']
    server = []
    while not set_state and time < wait_time:
        try:
            server = client.get_server_by_name(datacenter=datacenter, network_domain_id=network_domain_id, name=name)
        except NTTCCISAPIException as exc:
            module.fail_json(msg='Failed to get a list of servers - {0}'.format(exc.message), exception=traceback.format_exc())
        try:
            actual_state = server[0]['state']
            start_state = server[0]['started']
        except (KeyError, IndexError):
            module.fail_json(msg='Failed to find the server - {0}'.format(name))
        if actual_state != state or (check_for_start and not start_state) or (check_for_stop and start_state):
            sleep(wait_poll_interval)
            time = time + wait_poll_interval
        else:
            set_state = True

    if server and time >= wait_time:
        module.fail_json(msg='Timeout waiting for the server to be created')

    return server[0]


def main():
    """
    Main function
    :returns: Ansible Gateway Host Information
    """
    nttc_cis_regions = get_nttc_cis_regions()
    module = AnsibleModule(
        argument_spec=dict(
            region=dict(default='na', choices=nttc_cis_regions),
            datacenter=dict(required=True, type='str'),
            network_domain=dict(required=True, type='str'),
            vlan=dict(required=True, type='str'),
            name=dict(required=False, default='ansbile_gw', type='str'),
            password=dict(default=None, required=False, type='str'),
            ipv4=dict(default=None, required=False, type='str'),
            src_ip=dict(default='ANY', required=False, type='str'),
            src_prefix=dict(default=None, required=False, type='str'),
            state=dict(default='present', choices=['present', 'absent']),
            wait=dict(required=False, default=True, type='bool'),
            wait_time=dict(required=False, default=600, type='int'),
            wait_poll_interval=dict(required=False, default=30, type='int')
        )
    )

    credentials = get_credentials()
    name = module.params.get('name')
    datacenter = module.params.get('datacenter')
    state = module.params.get('state')
    network_domain_name = module.params.get('network_domain')
    vlan_name = module.params.get('vlan')
    vlan_id = None
    return_data = {}

    if credentials is False:
        module.fail_json(msg='Error: Could not load the user credentials')

    client = NTTCCISClient((credentials[0], credentials[1]), module.params['region'])

    # Get the CND object based on the supplied name
    try:
        network = client.get_network_domain_by_name(datacenter=datacenter, name=network_domain_name)
        network_domain_id = network['id']
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Failed to find the Cloud Network Domains - {0}'.format(exc.message))

    # Get the VLAN object based on the supplied name
    try:
        vlan = client.get_vlan_by_name(datacenter=datacenter, network_domain_id=network_domain_id, name=vlan_name)
        vlan_id = vlan.get('id')
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Failed to get a list of VLANs - {0}'.format(exc.message), exception=traceback.format_exc())

    # Check if the server exists based on the supplied name
    try:
        server = client.get_server_by_name(datacenter, network_domain_id, vlan_id, name)
    except (KeyError, IndexError, NTTCCISAPIException) as exc:
        module.fail_json(msg='Failed attempting to locate any existing server - {0}'.format(exc))

    # Hanldle the case where the gateway already exists. This could mean a playbook re-run
    # If the server exists then we need to check:
    #   a public IP is allocated and if not get the next one
    #   the NAT rule is present and correct and if not update/create it
    #   the Firewall rule is present and correct and if not update/create it
    if server:
        try:
            ansible_gw = server[0]
            ansible_gw_private_ipv4 = ansible_gw['networkInfo']['primaryNic']['privateIpv4']
            # Check if the NAT rule exists and if not create it
            nat_result = client.get_nat_by_private_ip(network_domain_id, ansible_gw['networkInfo']['primaryNic']['privateIpv4'])
            if nat_result:
                public_ipv4 = nat_result['externalIp']
            else:
                public_ipv4 = client.get_next_public_ipv4(network_domain_id)['ipAddress']
                create_nat_rule(module, client, network_domain_id, ansible_gw_private_ipv4, public_ipv4)
            # Check if the Firewall rule exists and if not create it
            fw_result = client.get_fw_rule_by_name(network_domain_id, ACL_RULE_NAME)
            if fw_result:
                update_fw_rule(module, client, fw_result, public_ipv4)
            else:
                create_fw_rule(module, client, network_domain_id, public_ipv4)
            return_data['server_id'] = ansible_gw.get('id')
            return_data['password'] = ansible_gw.get('password', None)
            return_data['internal_ipv4'] = ansible_gw.get('networkInfo').get('primaryNic').get('privateIpv4')
            return_data['ipv6'] = ansible_gw.get('networkInfo').get('primaryNic').get('ipv6')
            return_data['public_ipv4'] = public_ipv4.get('ipAddress')
            module.exit_json(changed=True, results=return_data)
        except (KeyError, IndexError):
            module.fail_json(msg='Could not ascertain the current server state')

    if state == 'present' and not server:
        try:
            ansible_gw = create_server(module, client, network_domain_id, vlan_id)
            ansible_gw_private_ipv4 = ansible_gw['networkInfo']['primaryNic']['privateIpv4']
            public_ipv4 = client.get_next_public_ipv4(network_domain_id)['ipAddress']
            return_data['server_id'] = ansible_gw.get('id')
            return_data['password'] = ansible_gw.get('password')
            return_data['internal_ipv4'] = ansible_gw.get('networkInfo').get('primaryNic').get('privateIpv4')
            return_data['ipv6'] = ansible_gw.get('networkInfo').get('primaryNic').get('ipv6')
            return_data['public_ipv4'] = public_ipv4.get('ipAddress')
            create_nat_rule(module, client, network_domain_id, ansible_gw_private_ipv4, public_ipv4)
            create_fw_rule(module, client, network_domain_id, public_ipv4.get('ipAddress'))
            # Sleep for 10 seconds to allow the CC API to implement the ACL before returning
            sleep(10)
            module.exit_json(changed=True, results=return_data)
        except (KeyError, IndexError, NTTCCISAPIException) as exc:
            module.fail_json(msg='Failed to create/update the Ansible gateway - {0}'.format(exc.message), exception=traceback.format_exc())


if __name__ == '__main__':
    main()
