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
module: nttc_cis_server_nic
short_description: Add, update or remove the NIC configuration for an existing server
description:
    - Add, update or remove the NIC configuration for an existing server
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
    network_domain:
        description:
            - The name of the Cloud Network Domain
        required: true
    server:
        description:
            - The name of the server
        required: true
    vlan:
        description:
            - The name of the VLAN for this NIC operation
            - servers can only have a single NIC in a given VLAN
        required: false
    ipv4_address:
        description:
            - The IPv4 address for for the NIC to be operated on
            - If both the VLAN and IPv4 address are supplied, the IPv4 address takes precendence
        required: false
    vlan_2:
        description:
            - The name of the VLAN for the secondary NIC when exchanging NIC VLANs
        required: false
    ipv4_address_2:
        description:
            - The IPv4 address for for the secondary NIC when exchanging NIC VLANs
            - If both the VLAN and IPv4 address are supplied, the IPv4 address takes precendence
        required: false
    type:
        description:
            - The type of NIC adapter
        required: false
        default: VMXNET3
        choices: ['VMXNET3', 'E1000']
    connected:
        description:
            - Should the NIC be connected
        required: false
        default: true
    stop:
        description:
            - Should the server be stopped if it is running
            - Disk operations can only be performed while the server is stopped
        required: false
        default: True
    start_after_upgrade:
        description:
            - Should the server be started after the disk operations have completed
        required: false
        default: true
    wait:
        description:
            - Should Ansible wait for the task to complete before continuing
        required: false
        default: true
        choices: [true, false]
    wait_time:
        description: The maximum time the Ansible should wait for the task
                     to complete in seconds
        required: false
        default: 600
    wait_poll_interval:
        description:
            - The time in between checking the status of the task in seconds
        required: false
        default: 10
notes:
    - N/A
'''

EXAMPLES = '''
# Add a NIC
nttc_cis_server_nic:
  region: na
  datacenter: NA9
  network_domain: "my_network_domain"
  server: "server01"
  type: E1000
  vlan: "my_vlan"
  state: present
# Change the NIC type
nttc_cis_server_nic:
  region: na
  datacenter: NA9
  network_domain: "my_network_domain"
  server: "server01"
  type: VMXNET3
  vlan: "my_vlan"
  state: present
# Exchange VLANs between two NICs
nttc_cis_server_nic:
  region: na
  datacenter: NA9
  network_domain: "my_network_domain"
  server: "server01"
  vlan: "my_vlan_1"
  vlan_2: "my_vlan_2"
  state: exchange
# Delete a NIC
nttc_cis_server_nic:
  region: na
  datacenter: NA9
  network_domain: "my_network_domain"
  server: "server01"
  ipv4_address: 172.16.1.6
  state: absent
'''

RETURN = '''
results:
    description: Server objects
    returned: success
    type: complex
    contains:
        started:
            description: Is the server running
            type: bool
            returned: when state == present and wait is True
        guest:
            description: Information about the guest OS
            type: complex
            returned: when state == present and wait is True
            contains:
                osCustomization:
                    description: Does the image support guest OS customization
                    type: bool
                vmTools:
                    description: VMWare Tools information
                    type: complex
                    contains:
                        type:
                            description: VMWare Tools or Open VM Tools
                            type: str
                            sample: VMWARE_TOOLS
                        runningStatus:
                            description: Is VMWare Tools running
                            type: str
                            sample: NOT_RUNNING
                        apiVersion:
                            description: The version of VMWare Tools
                            type: int
                            sample: 9256
                        versionStatus:
                            description: Additional information
                            type: str
                            sample: NEED_UPGRADE
                operatingSystem:
                    description: Operating system information
                    type: complex
                    contains:
                        displayName:
                            description: The OS display name
                            type: str
                            sample: CENTOS7/64
                        id:
                            description: The OS UUID
                            type: str
                            sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
                        family:
                            description: The OS family
                            type: str
                            sample: UNIX
                        osUnitsGroupId:
                            description: The OS billing group
                            type: str
                            sample: CENTOS
        source:
            description: The source of the image
            type: complex
            returned: when state == present and wait is True
            contains:
                type:
                    description: The id type of the image
                    type: str
                    sample: IMAGE_ID
                value:
                    description: The UUID of the image
                    type: str
                    sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
        floppy:
            description: List of the attached floppy drives
            type: complex
            returned: when state == present and wait is True
            contains:
                driveNumber:
                    description: The drive number
                    type: int
                    sample: 0
                state:
                    description: The state of the drive
                    type: str
                    sample: NORMAL
                id:
                    description: The UUID of the drive
                    type: str
                    sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
                key:
                    description: Internal usage
                    type: int
                    sample: 8000
        networkInfo:
            description: Server network information
            type: complex
            returned: when state == present and wait is True
            contains:
                networkDomainId:
                    description: The UUID of the Cloud Network Domain the server resides in
                    type: str
                    sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
                primaryNic:
                    description: The primary NIC on the server
                    type: complex
                    contains:
                        macAddress:
                            description: the MAC address
                            type: str
                            sample: aa:aa:aa:aa:aa:aa
                        vlanName:
                            description: The name of the VLAN the server resides in
                            type: str
                            sample: my_vlan
                        vlanId:
                            description: the UUID of the VLAN the server resides in
                            type: str
                            sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
                        state:
                            description: The state of the NIC
                            type: str
                            sample: NORMAL
                        privateIpv4:
                            description: The IPv4 address of the server
                            type: str
                            sample: 10.0.0.10
                        connected:
                            description: Is the NIC connected
                            type: bool
                        key:
                            description: Internal Usage
                            type: int
                            sample: 4000
                        ipv6:
                            description: The IPv6 address of the server
                            type: str
                            sample: "1111:1111:1111:1111:0:0:0:1"
                        networkAdapter:
                            description: The VMWare NIC type
                            type: str
                            sample: VMXNET3
                        id:
                            description: The UUID of the NIC
                            type: str
                            sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
        ideController:
            description: List of the server's IDE controllers
            type: complex
            returned: when state == present and wait is True
            contains:
                state:
                    description: The state of the controller
                    type: str
                    sample: NORMAL
                channel:
                    description: The IDE channel number
                    type: int
                    sample: 0
                key:
                    description: Internal Usage
                    type: int
                    sample: 200
                adapterType:
                    description: The type of the controller
                    type: str
                    sample: IDE
                id:
                    description: The UUID of the controller
                    type: str
                    sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
                deviceOrDisk:
                    description: List of the attached devices/disks
                    type: complex
                    contains:
                        device:
                            description: Device/Disk object
                            type: complex
                            contains:
                                slot:
                                    description: The slot number on the controller used by this device
                                    type: int
                                    sample: 0
                                state:
                                    description: The state of the device/disk
                                    type: str
                                    sample: NORMAL
                                type:
                                    description: The type of the device/disk
                                    type: str
                                    sample: CDROM
                                id:
                                    description: The UUID of the device/disk
                                    type: str
                                    sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
        createTime:
            description: The creation date of the server
            type: str
            returned: when state == present and wait is True
            sample: "2019-01-14T11:12:31.000Z"
        datacenterId:
            description: Datacenter id/location
            type: str
            returned: when state == present and wait is True
            sample: NA9
        scsiController:
            description: List of the SCSI controllers and disk configuration for the image
            type: complex
            returned: when state == present and wait is True
            contains:
                adapterType:
                    description: The name of the adapter
                    type: str
                    sample: "LSI_LOGIC_SAS"
                busNumber:
                    description: The SCSI bus number
                    type: int
                    sample: 1
                disk:
                    description: List of disks associated with this image
                    type: complex
                    contains:
                        id:
                            description: The disk id
                            type: str
                            sample: "112b7faa-ffff-ffff-ffff-dc273085cbe4"
                        scsiId:
                            description: The id of the disk on the SCSI controller
                            type: int
                            sample: 0
                        sizeGb:
                            description: The initial size of the disk in GB
                            type: int
                            sample: 10
                        speed:
                            description: The disk speed
                            type: str
                            sample: "STANDARD"
                id:
                    description: The SCSI controller id
                    type: str
                    sample: "112b7faa-ffff-ffff-ffff-dc273085cbe4"
                key:
                    description: Internal use
                    type: int
                    sample: 1000
        state:
            description: The state of the server
            type: str
            returned: when state == present and wait is True
            sample: NORMAL
        tag:
            description: List of informational tags associated with the server
            type: complex
            returned: when state == present and wait is True
            contains:
                value:
                    description: The tag value
                    type: str
                    sample: my_tag_value
                tagKeyName:
                    description: The tag name
                    type: str
                    sample: my_tag
                tagKeyId:
                    description: the UUID of the tag
                    type: str
                    sample: b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
        virtualHardware:
            description: Information on the virtual hardware of the server
            type: complex
            returned: when state == present and wait is True
            contains:
                upToDate:
                    description: Is the VM hardware up to date
                    type: bool
                version:
                    description: The VM hardware version
                    type: str
                    sample: VMX-10
        memoryGb:
            description: Server memory in GB
            type: int
            returned: when state == present and wait is True
            sample: 4
        id:
            description: The UUID of the server
            type: str
            returned: when state == present
            sample:  b2fbd7e6-ddbb-4eb6-a2dd-ad048bc5b9ae
        sataController:
            description: List of SATA controllers on the server
            type: list
            returned: when state == present and wait is True
            contains:
                adapterType:
                    description: The name of the adapter
                    type: str
                    sample: "LSI_LOGIC_SAS"
                busNumber:
                    description: The SCSI bus number
                    type: int
                    sample: 1
                disk:
                    description: List of disks associated with this image
                    type: complex
                    contains:
                        id:
                            description: The disk id
                            type: str
                            sample: "112b7faa-ffff-ffff-ffff-dc273085cbe4"
                        scsiId:
                            description: The id of the disk on the SCSI controller
                            type: int
                            sample: 0
                        sizeGb:
                            description: The initial size of the disk in GB
                            type: int
                            sample: 10
                        speed:
                            description: The disk speed
                            type: str
                            sample: "STANDARD"
                id:
                    description: The SCSI controller id
                    type: str
                    sample: "112b7faa-ffff-ffff-ffff-dc273085cbe4"
                key:
                    description: Internal use
                    type: int
                    sample: 1000
        cpu:
            description: The default CPU specifications for the image
            type: complex
            returned: when state == present and wait is True
            contains:
                coresPerSocket:
                    description: # of cores per CPU socket
                    type: int
                    sample: 1
                count:
                    description: The number of CPUs
                    type: int
                    sample: 2
                speed:
                    description: The CPU reservation to be applied
                    type: str
                    sample: "STANDARD"
        deployed:
            description: Is the server deployed
            type: bool
            returned: when state == present and wait is True
        name:
            description: The name of the server
            type: str
            returned: when state == present and wait is True
            sample: my_server
'''

import traceback
from time import sleep
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.nttc_cis.nttc_cis_utils import get_credentials, get_nttc_cis_regions
from ansible.module_utils.nttc_cis.nttc_cis_config import NIC_ADAPTER_TYPES
from ansible.module_utils.nttc_cis.nttc_cis_provider import NTTCCISClient, NTTCCISAPIException


def add_nic(module, client, network_domain_id, server, vlan):
    """
    Add a NIC to an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server to be updated
    :arg vlan: Dict containing the vlan of the NIC
    :returns: The updated server
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    nic_type = module.params.get('type')
    ipv4_address = module.params.get('ipv4_address')
    connected = module.params.get('connected')
    wait = module.params.get('wait')
    wait_poll_interval = module.params.get('wait_poll_interval')

    try:
        client.add_nic(server.get('id'), vlan.get('id'), ipv4_address, nic_type, connected)
        if wait:
            wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not create the controller - {0}'.format(e))


def get_nic(module, server, vlan, ipv4_address):
    """
    Get a NIC from an existing server

    :arg module: The Ansible module instance
    :arg server: The dict containing the server
    :arg ipv4_address: The IPv4 address of the NIC to be returned
    :returns: The controller(s)
    """
    nic_id = module.params.get('id')
    primary_nic = server.get('networkInfo').get('primaryNic')
    additional_nics = server.get('networkInfo').get('additionalNic')
    #module.exit_json(vlan=vlan, primary=primary_nic, add=additional_nics)
    if vlan:
        vlan_id = vlan.get('id')
    else:
        vlan_id = None

    try:
        if nic_id == primary_nic.get('id') or vlan_id == primary_nic.get('vlanId') or ipv4_address == primary_nic.get('privateIpv4'):
            return server.get('networkInfo').get('primaryNic')
        else:
            if additional_nics:
                for nic in additional_nics:
                    if nic_id == nic.get('id') or vlan_id == nic.get('vlanId') or ipv4_address == nic.get('privateIpv4'):
                        return nic
    except NTTCCISAPIException as e:
        module.fail_json(msg='There was an error attempting to find find the server NICs - {0}'.format(e))
    return None


def change_nic_type(module, client, network_domain_id, server, nic_id, nic_type):
    """
    Change a NIC on an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server
    :arg nic_id: The UUID of the NIC to be modified
    :arg nic_type: The new type of the NIC to be modified
    :returns: The NIC dict
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    module.params.get('wait')
    wait_poll_interval = module.params.get('wait_poll_interval')
    try:
        client.change_nic_type(nic_id, nic_type)
        if module.params.get('wait'):
            wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not change the type of NIC {0} - {1}'.format(nic_id, e))


def remove_nic(module, client, network_domain_id, server, nic):
    """
    Delete a NIC to an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server to be updated
    :arg nic: The dict containing the NIC to remove
    :returns: The updated server
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    module.params.get('wait')
    wait_poll_interval = module.params.get('wait_poll_interval')
    try:
        client.remove_nic(nic.get('id'))
        if module.params.get('wait'):
            wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not remove the NIC {0} - {1}'.format(nic.get('id'), e))


def exchange_nic(module, client, network_domain_id, server, nic_1, nic_2):
    """
    Swap VLANs for two NICs on an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server to be updated
    :arg nic_1: The dict containing NIC 1
    :arg nic_2: The dict containing NIC 2
    :returns: The updated server
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    module.params.get('wait')
    wait_poll_interval = module.params.get('wait_poll_interval')
    try:
        client.exchange_nic(nic_1.get('id'), nic_2.get('id'))
        if module.params.get('wait'):
            wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not remove the NICs {0} {1} - {2}'.format(nic_1.get('id'), nic_2.get('id'), e))

def check_and_stop_server(module, client, server, server_running):
    """
    Check and stop a running server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg server: The dict containing the server to be updated
    :arg server_running: Boolean denoting the current running status of the server
    :returns: The updated server
    """
    stop_server = module.params.get('stop')
    if server_running and stop_server:
        server_command(module, client, server, 'stop')
        return False
    elif server_running and not stop_server:
        module.fail_json(msg='NICs cannot be modified while the server is running')
    return True


def server_command(module, client, server, command):
    """
    Send a command to a server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg server: The dict containing the server to be updated
    :arg command: The CC server command
    :returns: The updated server
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    network_domain_id = server.get('networkInfo').get('networkDomainId')
    wait = module.params.get('wait')
    check_for_start = True
    check_for_stop = False
    # Set a default timer unless a lower one has been provided
    if module.params.get('wait_poll_interval') < 15:
        wait_poll_interval = module.params.get('wait_poll_interval')
    else:
        wait_poll_interval = 15

    try:
        if command == "start":
            client.start_server(server_id=server.get('id'))
        elif command == "reboot":
            client.reboot_server(server_id=server.get('id'))
        elif command == "stop":
            client.shutdown_server(server_id=server.get('id'))
            check_for_start = False
            check_for_stop = True
        if wait:
            wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', check_for_start, check_for_stop, wait_poll_interval)

    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not {0} the server - {1}'.format(command, e))


def wait_for_server(module, client, name, datacenter, network_domain_id, state, check_for_start=False, check_for_stop=False, wait_poll_interval=None):
    """
    Wait for an operation on a server. Polls based on wait_time and wait_poll_interval values.

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg name: The name of the server
    :arg datacenter: The name of a MCP datacenter
    :arg network_domain_id: The UUID of the Cloud Network Domain
    :arg state: The desired state to wait
    :arg check_for_start: Check if the server is started
    :arg check_for_stop: Check if the server is stopped
    :arg wait_poll_interval: The time between polls
    :returns: The server dict
    """
    set_state = False
    actual_state = ''
    start_state = ''
    time = 0
    wait_time = module.params.get('wait_time')
    if wait_poll_interval is None:
        wait_poll_interval = module.params.get('wait_poll_interval')
    server = []
    while not set_state and time < wait_time:
        try:
            servers = client.list_servers(datacenter=datacenter, network_domain_id=network_domain_id)
        except NTTCCISAPIException as e:
            module.fail_json(msg='Failed to get a list of servers - {0}'.format(e.message), exception=traceback.format_exc())
        server = [x for x in servers if x['name'] == name]
        try:
            actual_state = server[0]['state']
            start_state = server[0]['started']
        except (KeyError, IndexError) as e:
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

    :returns: Server Information
    """
    nttc_cis_regions = get_nttc_cis_regions()
    module = AnsibleModule(
        argument_spec=dict(
            region=dict(default='na', choices=nttc_cis_regions),
            datacenter=dict(required=True, type='str'),
            network_domain=dict(default=None, required=True, type='str'),
            server=dict(default=None, required=True, type='str'),
            vlan=dict(default=None, required=False, type='str'),
            vlan_2=dict(default=None, required=False, type='str'),
            ipv4_address=dict(default=None, required=False, type='str'),
            ipv4_address_2=dict(default=None, required=False, type='str'),
            type=dict(default='VMXNET3', required=False, choices=NIC_ADAPTER_TYPES),
            connected=dict(default=True, required=False, type='bool'),
            state=dict(default='present', choices=['present', 'absent', 'exchange']),
            stop=dict(default=True, type='bool'),
            start_after_update=dict(default=True, type='bool'),
            wait=dict(required=False, default=True, type='bool'),
            wait_time=dict(required=False, default=1200, type='int'),
            wait_poll_interval=dict(required=False, default=30, type='int')
        )
    )

    credentials = get_credentials()
    name = module.params.get('server')
    datacenter = module.params.get('datacenter')
    state = module.params.get('state')
    network_domain_name = module.params.get('network_domain')
    server_running = True
    changed = False
    vlan_name = module.params.get('vlan')
    vlan_name_2 = module.params.get('vlan_2')
    ipv4_address = module.params.get('ipv4_address')
    ipv4_address_2 = module.params.get('ipv4_address_2')
    start_after_update = module.params.get('start_after_update')
    server = {}


    if credentials is False:
        module.fail_json(msg='Could not load the user credentials')

    client = NTTCCISClient((credentials[0], credentials[1]), module.params.get('region'))

    # Get the CND object based on the supplied name
    try:
        if network_domain_name is None:
            module.fail_json(msg='No network_domain or network_info.network_domain was provided')
        network = client.get_network_domain_by_name(datacenter=datacenter, name=network_domain_name)
        network_domain_id = network.get('id')
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Failed to find the Cloud Network Domain: {0}'.format(network_domain_name))


    # Get a list of existing VLANs
    if vlan_name is not None:
        try:
            vlan = client.get_vlan_by_name(name=vlan_name, datacenter=datacenter, network_domain_id=network_domain_id)
        except NTTCCISAPIException as e:
            module.fail_json(msg='Failed to get a list of VLANs - {0}'.format(e))
    else:
        vlan = False
    if not vlan and ipv4_address is None:
        module.fail_json(msg='A valid VLAN name or IPv4 address must be supplied')


    # Get the secondary VLAN and or IPv4 address
    if vlan_name_2 is not None:
        try:
            vlan_2 = client.get_vlan_by_name(name=vlan_name_2, datacenter=datacenter, network_domain_id=network_domain_id)
        except NTTCCISAPIException as e:
            module.fail_json(msg='Failed to get a list of VLANs for the second VLAN - {0}'.format(e))
    else:
        vlan_2 = False
    if state == 'exchange' and not vlan and ipv4_address_2 is None:
        module.fail_json(msg='A valid secondary VLAN name or secondary IPv4 address is required for exchanging NIC VLANs')


    # Check if the Server exists based on the supplied name
    try:
        server = client.get_server_by_name(datacenter, network_domain_id, None, name)
        if server:
            server_running = server.get('started')
        else:
            module.fail_json(msg='Failed to find the server - {0}'.format(name))
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Failed attempting to locate any existing server - {0}'.format(e))

    if state == 'present':
        try:
            nic = get_nic(module, server, vlan, ipv4_address)
            if not nic:
                server_running = check_and_stop_server(module, client, server, server_running)
                add_nic(module, client, network_domain_id, server, vlan)
                changed = True
            else:
                if nic.get('networkAdapter') != module.params.get('type'):
                    server_running = check_and_stop_server(module, client, server, server_running)
                    change_nic_type(module, client, network_domain_id, server, nic.get('id'), module.params.get('type'))
                    changed = True
        except NTTCCISAPIException as e:
            module.fail_json(msg='Could not add the NIC - {0}'.format(e))
    elif state == 'absent':
        try:
            nic = get_nic(module, server, vlan, ipv4_address)
            if nic:
                server_running = check_and_stop_server(module, client, server, server_running)
                remove_nic(module, client, network_domain_id, server, nic)
                changed = True
            else:
                module.fail_json(msg='Server {0} has not matching NIC'.format(module.params.get('name')))
        except NTTCCISAPIException as e:
            module.fail_json(msg='Could not remove the NIC - {0}'.format(e))
    elif state == 'exchange':
        try:
            nic_1 = get_nic(module, server, vlan, ipv4_address)
            nic_2 = get_nic(module, server, vlan_2, ipv4_address_2)
            if nic_1 and nic_2:
                server_running = check_and_stop_server(module, client, server, server_running)
                exchange_nic(module, client, network_domain_id, server, nic_1, nic_2)
                changed = True
            else:
                module.fail_json(msg='Server {0} has no matching NICs'.format(module.params.get('server')))
        except NTTCCISAPIException as e:
            module.fail_json(msg='Could not exchange the server {0} has no matching NICs - {1}'.format(module.params.get('name'), e))
    try:
        if start_after_update and not server_running:
            server_command(module, client, server, 'start')
        server = client.get_server_by_name(datacenter, network_domain_id, None, name)
        module.exit_json(changed=changed, results=server)
    except NTTCCISAPIException as e:
        module.exit_json(changed=changed, msg='Could not verify the server status - {0}'.format(e))


if __name__ == '__main__':
    main()
