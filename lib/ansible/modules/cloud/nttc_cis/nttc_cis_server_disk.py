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
module: nttc_cis_server_disk
short_description: Alter the disk configuration for an existing server
description:
    - Alter the disk configuration for an existing server
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
    id:
        description:
            - The UUID of the disk
        required: false
    type:
        description:
            - The type of controller for this disk
        required: false
        default: SCSI
        choices: ['SCSI', 'SATA', 'IDE']
    controller_number:
        description:
            - The controller number on the controller as an integer
        required: false
        default: 0
    disk_number:
        description:
            - The disk number on the controller as an integer
        required: false
        default: 0
    size:
        description:
            - The new size of the disk as an integer
        required: false
    speed:
        description:
            - The new speed of the disk
        required: false
        default: STANDARD
        choices: ['STANDARD', 'ECONOMY', 'HIGHPERFORMANCE', 'PROVISIONEDIOPS']
    iops:
        description:
            - The IOPS for the disk as an integer
            - Only used for PROVISIONEDIOPS
        required: false
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
# Create a disk
- name: Add a disk to a server
  nttc_cis_server_disk:
    region: na
    datacenter: NA9
    network_domain: "my_network_domain"
    server: "server01"
    type: SCSI
    controller_number: 0
    speed: STANDARD
    state: present
# Update a Server
- name: Update a disk on a server
  nttc_cis_server_disk:
    region: na
    datacenter: NA9
    network_domain: "my_network_domain"
    server: "server01"
    type: SCSI
    controller_number: 0
    disk_number: 0
    speed: STANDARD
    state: present
# Delete a disk
- name: Delete a disk from a server
  nttc_cis_server_disk:
    region: na
    datacenter: NA9
    network_domain: "my_network_domain"
    name: "server01"
    controller_number: 0
    wait: True
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
                    description:
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
from copy import deepcopy
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.nttc_cis.nttc_cis_utils import get_credentials, get_nttc_cis_regions, compare_json
from ansible.module_utils.nttc_cis.nttc_cis_config import DISK_SPEEDS
from ansible.module_utils.nttc_cis.nttc_cis_provider import NTTCCISClient, NTTCCISAPIException


def add_disk(module, client, network_domain_id, server):
    """
    Add a disk to an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server to be updated
    :returns: The updated server
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    disk_speed = module.params.get('speed')
    disk_type = module.params.get('type')
    disk_iops = module.params.get('iops')
    disk_size = module.params.get('size')
    controller_number = module.params.get('controller_number')
    if controller_number is None:
        module.fail_json(msg='The controller number cannot be None')
    module.params.get('wait')
    wait_poll_interval = module.params.get('wait_poll_interval')

    if disk_type == 'SCSI':
        controller_name = 'scsiController'
    elif disk_type == 'SATA':
        controller_name = 'sataController'
    elif disk_type == 'IDE':
        controller_name = 'ideController'
    else:
        module.fail_json(msg='Invalid disk type.')

    try:
        device_number = len(server.get(controller_name))
        controller_id = server.get(controller_name)[controller_number].get('id')
        client.add_disk(controller_id, controller_name, device_number, disk_size, disk_speed, disk_iops)
        if module.params.get('wait'):
            wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not create the disk - {0}'.format(e))


def update_disk(module, client, network_domain_id, server, disk):
    """
    Update a disk on an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server to be updated
    :arg disk: The dict containing the disk to be udpated
    :returns: The updated server
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    disk_speed = module.params.get('speed')
    disk_id = disk.get('id')
    disk_iops = module.params.get('iops')
    disk_size = module.params.get('size')
    module.params.get('wait')
    wait_poll_interval = module.params.get('wait_poll_interval')
    try:
        if disk_speed is not None and disk_speed != disk.get('speed'):
            client.update_disk_speed(disk_id, disk_speed, disk_iops)
            if module.params.get('wait'):
                wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
        if disk_iops is not None and disk_iops != disk.get('iops'):
            client.update_disk_iops(disk_id, disk_iops)
            if module.params.get('wait'):
                wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
        if disk_size is not None and disk_size != disk.get('sizeGb'):
            expand_disk(module, client, server, disk)
            if module.params.get('wait'):
                wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Could not update the disk {0} - {1}'.format(disk.get('id'), e))


def compare_disk(module, existing_disk):
    """
    Compare two disks

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg existing_disk: The dict of the existing disk to be compared to
    :returns: Any differences between the two disk
    """
    new_disk = deepcopy(existing_disk)

    disk_size = module.params.get('size')
    disk_speed = module.params.get('speed')
    disk_iops = module.params.get('iops')

    if disk_size:
        new_disk['sizeGb'] = disk_size
    if disk_speed:
        new_disk['speed'] = disk_speed
    if disk_iops:
        new_disk['iops'] = disk_iops

    compare_result = compare_json(new_disk, existing_disk, None)
    return compare_result['changes']


def get_disk(module, server):
    """
    Get a disk to an existing server

    :arg module: The Ansible module instance
    :arg server: The dict containing the server
    :returns: The disk(s)
    """
    disk_type = module.params.get('type')
    disk_number = module.params.get('disk_number')
    if disk_number is None:
        return None
    controller_number = module.params.get('controller_number')
    if controller_number is None:
        module.fail_json(msg='The controller number cannot be None')
    if disk_type == 'SCSI':
        controller_name = 'scsiController'
    elif disk_type == 'SATA':
        controller_name = 'sataController'
    elif disk_type == 'IDE':
        controller_name = 'ideController'
    else:
        module.fail_json(msg='Invalid disk type.')

    try:
        return server.get(controller_name)[controller_number].get('disk')[disk_number]
    except (KeyError, IndexError, NTTCCISAPIException) as e:
        module.fail_json(msg='Could not locate any matching disk - {0}'.format(e))
    return None


def expand_disk(module, client, server, disk):
    """
    Expand a existing disk

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg server: The dict containing the server to be updated
    :arg disk: The dict containing the disk to be deleted
    :returns: The updated server
    """
    disk_id = disk.get('id')
    disk_size = module.params.get('size')
    if disk_id is None:
        module.fail_json(changed=False, msg='No disk id provided.')
    if disk_size is None:
        module.fail_json(msg='No size was provided. A value larger than 10 is required for disk_size.')
    server_id = server.get('id')
    try:
        client.expand_disk(server_id=server_id, disk_id=disk_id, disk_size=disk_size)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not expand the disk - {0}'.format(e))
    return True


def remove_disk(module, client, network_domain_id, server, disk):
    """
    Delete a disk to an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server to be updated
    :arg disk: The dict containing the disk to be deleted
    :returns: The updated server
    """
    name = server.get('name')
    datacenter = server.get('datacenterId')
    wait_poll_interval = module.params.get('wait_poll_interval')
    try:
        client.remove_disk(disk.get('id'))
        if module.params.get('wait'):
            wait_for_server(module, client, name, datacenter, network_domain_id, 'NORMAL', False, False, wait_poll_interval)
    except NTTCCISAPIException as e:
        module.fail_json(msg='Could not remove the disk {0} - {1}'.format(disk.get('id'), e))



def server_command(module, client, server, command):
    """
    Add a controller to an existing server

    :arg module: The Ansible module instance
    :arg client: The CC API client instance
    :arg network_domain_id: The UUID of the network domain
    :arg server: The dict containing the server to be updated
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
            server=dict(required=True, type='str'),
            id=dict(default=None, required=False, type='str'),
            type=dict(default='SCSI', required=False, choices=['SCSI', 'SATA', 'IDE']),
            controller_number=dict(default=None, required=False, type='int'),
            disk_number=dict(default=None, required=False, type='int'),
            size=dict(required=False, type='int'),
            speed=dict(default='STANDARD', required=False, choices=DISK_SPEEDS),
            iops=dict(default=None, required=False, type='int'),
            state=dict(default='present', choices=['present', 'absent']),
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
    stop_server = module.params.get('stop')
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
        disk = get_disk(module, server)
        if not disk:
            if server_running and stop_server:
                server_command(module, client, server, 'stop')
                server_running = False
            elif server_running and not stop_server:
                module.fail_json(msg='Server disks cannot be added while the server is running')
            add_disk(module, client, network_domain_id, server)
            if start_after_update and not server_running:
                server_command(module, client, server, 'start')
            server = client.get_server_by_name(datacenter, network_domain_id, None, name)
            module.exit_json(changed=True, results=server)
        else:
            try:
                if compare_disk(module, disk):
                    if server_running and stop_server:
                        server_command(module, client, server, 'stop')
                        server_running = False
                    elif server_running and not stop_server:
                        module.fail_json(msg='Server disks cannot be added while the server is running')
                    update_disk(module, client, network_domain_id, server, disk)
                else:
                    module.exit_json(changed=False, results=server)
                if start_after_update and not server_running:
                    server_command(module, client, server, 'start')
                server = client.get_server_by_name(datacenter, network_domain_id, None, name)
                module.exit_json(changed=True, results=server)
            except NTTCCISAPIException as e:
                module.fail_json(msg='Failed to update the disk - {0}'.format(e))
    elif state == 'absent':
        try:
            disk = get_disk(module, server)
            if server_running and stop_server:
                server_command(module, client, server, 'stop')
                server_running = False
            elif server_running and not stop_server:
                module.fail_json(msg='Disks cannot be removed while the server is running')
            if not disk:
                module.fail_json(msg='Controller {0} has no disk {1}'.format(module.params.get('controller_number'), module.params.get('disk_number')))
            remove_disk(module, client, network_domain_id, server, disk)
            if start_after_update and not server_running:
                server_command(module, client, server, 'start')
            server = client.get_server_by_name(datacenter, network_domain_id, None, name)
            module.exit_json(changed=True, results=server)
        except (KeyError, IndexError, NTTCCISAPIException) as e:
            module.fail_json(msg='Could not delete the disk - {0}'.format(e))


if __name__ == '__main__':
    main()
