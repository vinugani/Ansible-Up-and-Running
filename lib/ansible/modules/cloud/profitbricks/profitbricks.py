#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: profitbricks
short_description: Create, update, destroy, start, stop, and reboot a ProfitBricks virtual machine.
description:
     - Create, update, destroy, update, start, stop, and reboot a ProfitBricks virtual machine.
       When the virtual machine is created it can optionally wait for it to be 'running' before returning.
version_added: "2.0"
options:
  auto_increment:
    description:
      - Whether or not to increment a single number in the name for created virtual machines.
    type: bool
    default: true
  name:
    description:
      - The name of the virtual machine.
    required: true
  image:
    description:
      - The image alias or ID for creating the virtual machine.
    required: true
  image_password:
    description:
      - Password set for the administrative user.
    required: false
    version_added: "2.2"
  ssh_keys:
    description:
      - Public SSH keys allowing access to the virtual machine.
    required: false
    version_added: "2.2"
  volume_availability_zone:
    description:
      - The storage availability zone assigned to the volume.
    required: false
    default: none
    choices: [ "AUTO", "ZONE_1", "ZONE_2", "ZONE_3" ]
    version_added: "2.6"
  datacenter:
    description:
      - The datacenter to provision this virtual machine.
    required: false
    default: null
  cores:
    description:
      - The number of CPU cores to allocate to the virtual machine.
    required: false
    default: 2
  ram:
    description:
      - The amount of memory to allocate to the virtual machine.
    required: false
    default: 2048
  cpu_family:
    description:
      - The CPU family type to allocate to the virtual machine.
    required: false
    default: AMD_OPTERON
    choices: [ "AMD_OPTERON", "INTEL_XEON" ]
    version_added: "2.2"
  availability_zone:
    description:
      - The availability zone assigned to the server.
    required: false
    default: AUTO
    choices: [ "AUTO", "ZONE_1", "ZONE_2" ]
    version_added: "2.6"
  volume_size:
    description:
      - The size in GB of the boot volume.
    required: false
    default: 10
  bus:
    description:
      - The bus type for the volume.
    required: false
    default: VIRTIO
    choices: [ "IDE", "VIRTIO"]
  instance_ids:
    description:
      - list of instance ids, currently only used when state='absent' to remove instances.
    required: false
  count:
    description:
      - The number of virtual machines to create.
    required: false
    default: 1
  location:
    description:
      - The datacenter location. Use only if you want to create the Datacenter or else this value is ignored.
    required: false
    default: us/las
    choices: [ "us/las", "us/ewr", "de/fra", "de/fkb" ]
  assign_public_ip:
    description:
      - This will assign the machine to the public LAN. If no LAN exists with public Internet access it is created.
    type: bool
    required: false
    default: false
  lan:
    description:
      - The ID of the LAN you wish to add the servers to.
    required: false
    default: 1
  nat:
    description:
      - Boolean value indicating if the private IP address has outbound access to the public Internet.
    type: bool
    required: false
    default: false
    version_added: "2.6"
  api_url:
    description:
      - The ProfitBricks API base URL.
    required: false
    default: none
    version_added: "2.6"
  username:
    description:
      - The ProfitBricks username. Overrides the PROFITBRICKS_USERNAME environment variable.
    required: false
    aliases:
      - subscription_user
  password:
    description:
      - The ProfitBricks password. Overrides the PROFITBRICKS_PASSWORD environment variable.
    required: false
    aliases:
      - subscription_password
  wait:
    description:
      - wait for the instance to be in state 'running' before returning
    type: bool
    required: false
    default: true
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 600
  remove_boot_volume:
    description:
      - remove the bootVolume of the virtual machine you're destroying.
    type: bool
    required: false
    default: true
  state:
    description:
      - Indicate desired state of the resource
    required: false
    default: "present"
    choices: [ "running", "stopped", "absent", "present", "update" ]

requirements:
    - "python >= 2.6"
    - "profitbricks >= 4.0.0"
author:
    - "Matt Baldwin (baldwin@stackpointcloud.com)"
    - "Ethan Devenport (@edevenport)"
'''

EXAMPLES = '''

# Provisioning example. This will create three servers and enumerate their names.

- profitbricks:
    datacenter: Tardis One
    name: web%02d.stackpointcloud.com
    cores: 4
    ram: 2048
    volume_size: 50
    cpu_family: INTEL_XEON
    image: ubuntu:latest
    location: us/las
    count: 3
    assign_public_ip: true

# Update Virtual machines

- profitbricks:
    datacenter: Tardis One
    instance_ids:
      - web001.stackpointcloud.com
      - web002.stackpointcloud.com
    cores: 4
    ram: 4096
    cpu_family: INTEL_XEON
    availability_zone: ZONE_1
    state: update

# Removing Virtual machines

- profitbricks:
    datacenter: Tardis One
    instance_ids:
      - 'web001.stackpointcloud.com'
      - 'web002.stackpointcloud.com'
      - 'web003.stackpointcloud.com'
    wait_timeout: 500
    state: absent

# Starting Virtual Machines.

- profitbricks:
    datacenter: Tardis One
    instance_ids:
      - 'web001.stackpointcloud.com'
      - 'web002.stackpointcloud.com'
      - 'web003.stackpointcloud.com'
    wait_timeout: 500
    state: running

# Stopping Virtual Machines

- profitbricks:
    datacenter: Tardis One
    instance_ids:
      - 'web001.stackpointcloud.com'
      - 'web002.stackpointcloud.com'
      - 'web003.stackpointcloud.com'
    wait_timeout: 500
    state: stopped

'''

import time
import traceback

from uuid import (uuid4, UUID)

HAS_PB_SDK = True

try:
    from profitbricks import __version__ as sdk_version
    from profitbricks.client import (ProfitBricksService, Volume, Server,
                                     Datacenter, NIC, LAN)
except ImportError:
    HAS_PB_SDK = False

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils.six.moves import xrange
from ansible.module_utils._text import to_native
from ansible.module_utils.profitbricks import (
    AVAILABILITY_ZONES,
    BUS_TYPES,
    CPU_FAMILIES,
    DISK_TYPES,
    LOCATIONS,
    get_resource_id,
    wait_for_completion
)


def _create_machine(module, profitbricks, datacenter, name):
    cores = module.params.get('cores')
    ram = module.params.get('ram')
    cpu_family = module.params.get('cpu_family')
    volume_size = module.params.get('volume_size')
    disk_type = module.params.get('disk_type')
    availability_zone = module.params.get('availability_zone')
    volume_availability_zone = module.params.get('volume_availability_zone')
    image_password = module.params.get('image_password')
    ssh_keys = module.params.get('ssh_keys')
    bus = module.params.get('bus')
    lan = module.params.get('lan')
    nat = module.params.get('nat')
    image = module.params.get('image')
    assign_public_ip = module.boolean(module.params.get('assign_public_ip'))
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    if assign_public_ip:
        public_found = False

        lans = profitbricks.list_lans(datacenter)
        for lan in lans['items']:
            if lan['properties']['public']:
                public_found = True
                lan = lan['id']

        if not public_found:
            i = LAN(
                name='public',
                public=True)

            lan_response = profitbricks.create_lan(datacenter, i)
            wait_for_completion(profitbricks, lan_response,
                                wait_timeout, "_create_machine")
            lan = lan_response['id']

    v = Volume(
        name=str(uuid4()).replace('-', '')[:10],
        size=volume_size,
        image_password=image_password,
        ssh_keys=ssh_keys,
        disk_type=disk_type,
        availability_zone=volume_availability_zone,
        bus=bus
    )

    try:
        UUID(image)
    except Exception:
        v.image_alias = image
    else:
        v.image = image

    n = NIC(
        name=str(uuid4()).replace('-', '')[:10],
        nat=nat,
        lan=int(lan)
    )

    s = Server(
        name=name,
        ram=ram,
        cores=cores,
        cpu_family=cpu_family,
        availability_zone=availability_zone,
        create_volumes=[v],
        nics=[n],
    )

    try:
        create_server_response = profitbricks.create_server(
            datacenter_id=datacenter, server=s)

        wait_for_completion(profitbricks, create_server_response,
                            wait_timeout, "create_virtual_machine")

        server_response = profitbricks.get_server(
            datacenter_id=datacenter,
            server_id=create_server_response['id'],
            depth=3
        )
    except Exception as e:
        module.fail_json(msg="failed to create the new server: %s" % to_native(e))
    else:
        server_response['nic'] = server_response['entities']['nics']['items'][0]
        return server_response


def _startstop_machine(module, profitbricks, datacenter_id, server_id):
    state = module.params.get('state')

    try:
        if state == 'running':
            profitbricks.start_server(datacenter_id, server_id)
        else:
            profitbricks.stop_server(datacenter_id, server_id)

        return True
    except Exception as e:
        module.fail_json(
            msg="failed to start or stop the virtual machine %s at %s: %s" % (server_id, datacenter_id, to_native(e)))


def _create_datacenter(module, profitbricks):
    datacenter = module.params.get('datacenter')
    location = module.params.get('location')
    wait_timeout = module.params.get('wait_timeout')

    i = Datacenter(
        name=datacenter,
        location=location
    )

    try:
        datacenter_response = profitbricks.create_datacenter(datacenter=i)

        wait_for_completion(profitbricks, datacenter_response,
                            wait_timeout, "_create_datacenter")

        return datacenter_response
    except Exception as e:
        module.fail_json(msg="failed to create the new server(s): %s" % to_native(e))


def create_virtual_machine(module, profitbricks):
    """
    Create new virtual machine

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object

    Returns:
        True if a new virtual machine was created, false otherwise
    """
    datacenter = module.params.get('datacenter')
    name = module.params.get('name')
    auto_increment = module.params.get('auto_increment')
    count = module.params.get('count')
    lan = module.params.get('lan')
    wait_timeout = module.params.get('wait_timeout')
    datacenter_found = False

    virtual_machines = []

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = get_resource_id(datacenter_list, datacenter)
    if datacenter_id:
        datacenter_found = True

    if not datacenter_found:
        datacenter_response = _create_datacenter(module, profitbricks)
        datacenter_id = datacenter_response['id']

        wait_for_completion(profitbricks, datacenter_response,
                            wait_timeout, "create_virtual_machine")

    if auto_increment:
        numbers = set()
        count_offset = 1

        try:
            name % 0
        except TypeError as e:
            if e.message and e.message.startswith('not all'):
                name = '%s%%d' % name
            else:
                module.fail_json(msg=e.message, exception=traceback.format_exc())

        number_range = xrange(count_offset, count_offset + count + len(numbers))
        available_numbers = list(set(number_range).difference(numbers))
        names = []
        numbers_to_use = available_numbers[:count]
        for number in numbers_to_use:
            names.append(name % number)
    else:
        names = [name]

    # Prefetch a list of servers for later comparison.
    server_list = profitbricks.list_servers(datacenter_id)
    for name in names:
        # Skip server creation if the server already exists.
        if get_resource_id(server_list, name):
            continue

        create_response = _create_machine(module, profitbricks, str(datacenter_id), name)
        nics = profitbricks.list_nics(datacenter_id, create_response['id'])
        for n in nics['items']:
            if lan == n['properties']['lan']:
                create_response.update({'public_ip': n['properties']['ips'][0]})

        virtual_machines.append(create_response)

    results = {
        'failed': False,
        'machines': virtual_machines,
        'action': 'create',
        'instance_ids': {
            'instances': [i['id'] for i in virtual_machines],
        }
    }

    return results


def update_server(module, profitbricks):
    """
    Update servers.

    This will update one or more servers.

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object.

    Returns:
        dict of updated servers
    """
    datacenter = module.params.get('datacenter')
    instance_ids = module.params.get('instance_ids')

    if not isinstance(module.params.get('instance_ids'), list) or len(module.params.get('instance_ids')) < 1:
        module.fail_json(msg='instance_ids should be a list of virtual machine ids or names, aborting')

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = get_resource_id(datacenter_list, datacenter)
    if not datacenter_id:
        module.fail_json(msg='Virtual data center \'%s\' not found.' % str(datacenter))

    updated_servers = []

    cores = module.params.get('cores')
    ram = module.params.get('ram')
    cpu_family = module.params.get('cpu_family')
    availability_zone = module.params.get('availability_zone')
    allow_reboot = None

    server_list = profitbricks.list_servers(datacenter_id)
    for instance in instance_ids:
        server = None
        for s in server_list['items']:
            if instance in (s['properties']['name'], s['id']):
                server = s
                break

        if not server:
            module.fail_json(msg='Server \'%s\' not found.' % str(instance))

        if cpu_family != server['properties']['cpuFamily']:
            allow_reboot = True

        if module.check_mode:
            module.exit_json(changed=True)

        try:
            update_response = profitbricks.update_server(
                datacenter_id,
                server['id'],
                cores=cores,
                ram=ram,
                cpu_family=cpu_family,
                availability_zone=availability_zone,
                allow_reboot=allow_reboot
            )
        except Exception as e:
            module.fail_json(msg="failed to update the server: %s" % to_native(e), exception=traceback.format_exc())
        else:
            updated_servers.append(update_response)

    results = {
        'failed': False,
        'machines': updated_servers,
        'action': 'update',
        'instance_ids': {
            'instances': [i['id'] for i in updated_servers],
        }
    }

    return results


def remove_virtual_machine(module, profitbricks):
    """
    Removes a virtual machine.

    This will remove the virtual machine along with the bootVolume.

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object.

    Not yet supported: handle deletion of attached data disks.

    Returns:
        True if a new virtual server was deleted, false otherwise
    """
    datacenter = module.params.get('datacenter')
    instance_ids = module.params.get('instance_ids')
    remove_boot_volume = module.params.get('remove_boot_volume')
    changed = False

    if not isinstance(module.params.get('instance_ids'), list) or len(module.params.get('instance_ids')) < 1:
        module.fail_json(msg='instance_ids should be a list of virtual machine ids or names, aborting')

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = get_resource_id(datacenter_list, datacenter)
    if not datacenter_id:
        module.fail_json(msg='Virtual data center \'%s\' not found.' % str(datacenter))

    # Prefetch server list for later comparison.
    server_list = profitbricks.list_servers(datacenter_id)
    for instance in instance_ids:
        # Locate UUID for server if referenced by name.
        server_id = get_resource_id(server_list, instance)
        if server_id:
            if module.check_mode:
                module.exit_json(changed=True)

            # Remove the server's boot volume
            if remove_boot_volume:
                _remove_boot_volume(module, profitbricks, datacenter_id, server_id)

            # Remove the server
            try:
                profitbricks.delete_server(datacenter_id, server_id)
            except Exception as e:
                module.fail_json(msg="failed to terminate the virtual server: %s" % to_native(e), exception=traceback.format_exc())
            else:
                changed = True

    return changed


def _remove_boot_volume(module, profitbricks, datacenter_id, server_id):
    """
    Remove the boot volume from the server
    """
    try:
        server = profitbricks.get_server(datacenter_id, server_id)
        volume_id = server['properties']['bootVolume']['id']
        profitbricks.delete_volume(datacenter_id, volume_id)
    except Exception as e:
        module.fail_json(msg="failed to remove the server's boot volume: %s" % to_native(e), exception=traceback.format_exc())


def startstop_machine(module, profitbricks, state):
    """
    Starts or Stops a virtual machine.

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object.

    Returns:
        True when the servers process the action successfully, false otherwise.
    """
    if not isinstance(module.params.get('instance_ids'), list) or len(module.params.get('instance_ids')) < 1:
        module.fail_json(msg='instance_ids should be a list of virtual machine ids or names, aborting')

    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    changed = False

    datacenter = module.params.get('datacenter')
    instance_ids = module.params.get('instance_ids')

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = get_resource_id(datacenter_list, datacenter)
    if not datacenter_id:
        module.fail_json(msg='Virtual data center \'%s\' not found.' % str(datacenter))

    # Prefetch server list for later comparison.
    server_list = profitbricks.list_servers(datacenter_id)
    for instance in instance_ids:
        # Locate UUID of server if referenced by name.
        server_id = get_resource_id(server_list, instance)
        if server_id:
            if module.check_mode:
                module.exit_json(changed=True)

            _startstop_machine(module, profitbricks, datacenter_id, server_id)
            changed = True

    if wait:
        wait_timeout = time.time() + wait_timeout
        while wait_timeout > time.time():
            matched_instances = []
            for res in profitbricks.list_servers(datacenter_id)['items']:
                if state == 'running':
                    if res['properties']['vmState'].lower() == state:
                        matched_instances.append(res)
                elif state == 'stopped':
                    if res['properties']['vmState'].lower() in ['shutoff', 'shutdown', 'inactive']:
                        matched_instances.append(res)

            if len(matched_instances) < len(instance_ids):
                time.sleep(5)
            else:
                break

        if wait_timeout <= time.time():
            # waiting took too long
            module.fail_json(msg="wait for virtual machine state timeout on %s" % time.asctime())

    return (changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            datacenter=dict(type='str'),
            name=dict(type='str'),
            image=dict(type='str'),
            cores=dict(type='int', default=2),
            ram=dict(type='int', default=2048),
            cpu_family=dict(type='str', choices=CPU_FAMILIES, default='AMD_OPTERON'),
            volume_size=dict(type='int', default=10),
            disk_type=dict(type='str', choices=DISK_TYPES, default='HDD'),
            availability_zone=dict(type='str', choices=AVAILABILITY_ZONES, default='AUTO'),
            volume_availability_zone=dict(type='str', choices=AVAILABILITY_ZONES, default=None),
            image_password=dict(type='str', default=None, no_log=True),
            ssh_keys=dict(type='list', default=[]),
            bus=dict(type='str', choices=BUS_TYPES, default='VIRTIO'),
            lan=dict(type='int', default=1),
            nat=dict(type='bool', default=None),
            count=dict(type='int', default=1),
            auto_increment=dict(type='bool', default=True),
            instance_ids=dict(type='list', default=[]),
            api_url=dict(type='str', default=None),
            username=dict(
                required=True,
                aliases=['subscription_user'],
                fallback=(env_fallback, ['PROFITBRICKS_USERNAME'])
            ),
            password=dict(
                required=True,
                aliases=['subscription_password'],
                fallback=(env_fallback, ['PROFITBRICKS_PASSWORD']),
                no_log=True
            ),
            location=dict(type='str', choices=LOCATIONS, default='us/las'),
            assign_public_ip=dict(type='bool', default=False),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(type='int', default=600),
            remove_boot_volume=dict(type='bool', default=True),
            state=dict(type='str', default='present'),
        ),
        supports_check_mode=True
    )

    if not HAS_PB_SDK:
        module.fail_json(msg='profitbricks required for this module')

    username = module.params.get('username')
    password = module.params.get('password')
    api_url = module.params.get('api_url')

    if not api_url:
        profitbricks = ProfitBricksService(username=username, password=password)
    else:
        profitbricks = ProfitBricksService(
            username=username,
            password=password,
            host_base=api_url
        )

    user_agent = 'profitbricks-sdk-python/%s Ansible/%s' % (sdk_version, module.ansible_version)
    profitbricks.headers = {'User-Agent': user_agent}

    state = module.params.get('state')

    if state == 'absent':
        if not module.params.get('datacenter'):
            module.fail_json(msg='datacenter parameter is required for running or stopping machines.')

        try:
            (changed) = remove_virtual_machine(module, profitbricks)
            module.exit_json(changed=changed)
        except Exception as e:
            module.fail_json(msg='failed to set instance state: %s' % to_native(e), exception=traceback.format_exc())

    elif state in ('running', 'stopped'):
        if not module.params.get('datacenter'):
            module.fail_json(msg='datacenter parameter is required for running or stopping machines.')
        try:
            (changed) = startstop_machine(module, profitbricks, state)
            module.exit_json(changed=changed)
        except Exception as e:
            module.fail_json(msg='failed to set instance state: %s' % to_native(e), exception=traceback.format_exc())

    elif state == 'present':
        if not module.params.get('name'):
            module.fail_json(msg='name parameter is required for new instance')
        if not module.params.get('image'):
            module.fail_json(msg='image parameter is required for new instance')

        if module.check_mode:
            module.exit_json(changed=True)

        try:
            (machine_dict_array) = create_virtual_machine(module, profitbricks)
            module.exit_json(**machine_dict_array)
        except Exception as e:
            module.fail_json(msg='failed to set instance state: %s' % to_native(e), exception=traceback.format_exc())

    elif state == 'update':
        try:
            (machine_dict_array) = update_server(module, profitbricks)
            module.exit_json(**machine_dict_array)
        except Exception as e:
            module.fail_json(msg='failed to update server: %s' % to_native(e), exception=traceback.format_exc())


if __name__ == '__main__':
    main()
