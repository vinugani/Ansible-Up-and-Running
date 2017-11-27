#!/usr/bin/python
#
# Copyright (c) 2017 Yuwei Zhou, <yuwzho@microsoft.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
---
module: azure_rm_image
version_added: "2.5"
short_description: Manage Azure image.
description:
    - Create, delete an image from virtual machine, blob uri, managed disk or snapshot.
options:
    resource_group:
        description:
            - Name of resource group.
        required: true
    name:
        description:
            - Name of the image.
        required: true
    source:
        description:
            - OS disk source from the same region, including a virtual machine id or name,
              OS disk blob uri, managed OS disk id or name, or OS snapshot id or name.
        required: true
    data_disk_sources:
        description:
            - List of data disk sources, including unmanaged blob uri, managed disk id or name, or snapshot id or name.
    location:
        description:
            - Location of the image.
    os_type:
        description: The OS type of image.
        choices:
            - Windows
            - Linux
    state:
        description:
            - Assert the state of the image. Use 'present' to create or update a image and 'absent' to delete an image.
        default: present
        choices:
            - absent
            - present

extends_documentation_fragment:
    - azure
    - azure_tags

author:
    - "Yuwei Zhou (@yuwzho)"

'''

EXAMPLES = '''
- name: Create an image from a virtual machine
  azure_rm_image:
    resource_group: Testing
    name: foobar
    source: testvm001

- name: Create an image from os disk
  azure_rm_image:
    resource_group: Testing
    name: foobar
    source: /subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Compute/disks/disk001
    data_disk_sources:
        - datadisk001
        - datadisk002
    os_type: Linux

- name: Delete an image
  azure_rm_image:
    state: absent
    resource_group: Testing
    name: foobar
    source: testvm001
'''

RETURN = '''
state:
    description: Current state of the image.
    returned: success
    type: complex
    contains:
        id:
          description: Image resource path.
          type: str
          example: "/subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Compute/images/foobar"
        name:
          description: Image name.
          type: str
          example: "foobar"
        location:
          description: Location of the image
          type: str
          example: "eastus"
        resource_group:
          description: Resource group of the image
          type: str
          example: "Testing"
        provisioning_state:
          description: Success or failure of the provisioning event.
          type: str
          example: "Succeeded"
        properties:
          description: Facts about the current image
          type: complex
          contains: {
              "storageProfile": {
                "osDisk": {
                "storageAccountType": "Standard_LRS",
                "managedDisk": {
                    "id": "/subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Compute/disks/testvm001"
                },
                "diskSizeGB": 32,
                "osState": "Generalized",
                "caching": "ReadOnly",
                "osType": "Linux"
                },
                "dataDisks": [
                    {
                        "caching": "ReadOnly",
                        "diskSizeGB": 64,
                        "storageAccountType": "Standard_LRS",
                        "managedDisk": {
                        "id": "/subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Compute/disks/testvm001-datadisk-0"
                        },
                        "lun": 0
                    }
                ]
            },
            "sourceVirtualMachine": {
                "id": "/subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Compute/virtualMachines/testvm001"
            }
          }
'''  # NOQA

from ansible.module_utils.azure_rm_common import AzureRMModuleBase, format_resource_id

try:
    from msrestazure.tools import parse_resource_id
    from msrestazure.azure_exceptions import CloudError
    from azure.mgmt.compute.models import SubResource, OperatingSystemStateTypes, ImageStorageProfile, Image, ImageOSDisk, ImageDataDisk
except ImportError:
    # This is handled in azure_rm_common
    pass


class AzureRMImage(AzureRMModuleBase):

    def __init__(self):

        self.module_arg_spec = dict(
            resource_group=dict(type='str', required=True),
            name=dict(type='str', required=True),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            location=dict(type='str'),
            source=dict(type='str', required=True),
            data_disk_sources=dict(type='list', default=[]),
            os_type=dict(type='str', choices=['Windows', 'Linux'])
        )

        self.results = dict(
            changed=False,
            state=dict()
        )

        self.resource_group = None
        self.name = None
        self.state = None
        self.location = None
        self.source = None
        self.data_disk_sources = None
        self.os_type = None
        self.tags = None

        super(AzureRMImage, self).__init__(self.module_arg_spec, supports_check_mode=True)

    def exec_module(self, **kwargs):

        for key in self.module_arg_spec:
            setattr(self, key, kwargs[key])

        results = dict()
        changed = False
        image = None

        if not self.location:
            # Set default location
            resource_group = self.get_resource_group(self.resource_group)
            self.location = resource_group.location

        self.log('Fetching image {0}'.format(self.name))
        image = self.get_image()
        if image:
            self.check_provisioning_state(image, self.state)
            results = self._image_to_dict(image)
            # update is not supported
            if self.state == 'absent':
                changed = True
        # the image does not exist and create a new one
        elif self.state == 'present':
            changed = True

        self.results['changed'] = changed
        self.results['state'] = results

        if changed:
            if self.state == 'present':
                image_instance = None
                # create from virtual machine
                vm = self.get_source_vm()
                if vm:
                    if self.data_disk_sources:
                        self.fail('data_disk_sources is not allowed when capturing image from vm')
                    image_instance = Image(self.location, source_virtual_machine=SubResource(vm.id))
                else:
                    if not self.os_type:
                        self.fail('os_type is required to create the image')
                    os_disk = self.create_os_disk()
                    data_disks = self.create_data_disks()
                    storage_profile = ImageStorageProfile(os_disk=os_disk, data_disks=data_disks)
                    image_instance = Image(self.location, storage_profile=storage_profile, tags=self.tags)

                # finally make the change if not check mode
                if not self.check_mode and image_instance:
                    new_image = self.create_image(image_instance)
                    self.results['state'] = self._image_to_dict(new_image)

            elif self.state == 'absent':
                if not self.check_mode:
                    # delete image
                    self.delete_image()
                # the delete does not actually return anything. if no exception, then we'll assume it worked.
                self.results['state']['status'] = 'Deleted'

        return self.results

    def _image_to_dict(self, image):
        return image.as_dict()

    def resolve_storage_source(self, source):
        blob_uri = None
        disk = None
        snapshot = None
        if source.lower().endswith('.vhd'):
            blob_uri = source
            return (blob_uri, disk, snapshot)

        tokenize = parse_resource_id(source)
        if tokenize.get('type') == 'disks':
            disk = source
            return (blob_uri, disk, snapshot)

        if tokenize.get('type') == 'snapshots':
            snapshot = source
            return (blob_uri, disk, snapshot)

        # not a disk or snapshots
        if 'type' in tokenize:
            return (blob_uri, disk, snapshot)

        # source can be name of snapshot or disk
        snapshot_instance = self.get_snapshot(source)
        if snapshot_instance:
            snapshot = snapshot_instance.id
            return (blob_uri, disk, snapshot)

        disk_instance = self.get_disk(source)
        if disk_instance:
            disk = disk_instance.id
        return (blob_uri, disk, snapshot)

    def create_os_disk(self):
        blob_uri, disk, snapshot = self.resolve_storage_source(self.source)
        snapshot_resource = SubResource(snapshot) if snapshot else None
        managed_disk = SubResource(disk) if disk else None
        return ImageOSDisk(os_type=self.os_type,
                           os_state=OperatingSystemStateTypes.generalized,
                           snapshot=snapshot_resource,
                           managed_disk=managed_disk,
                           blob_uri=blob_uri)

    def create_data_disk(self, lun, source):
        blob_uri, disk, snapshot = self.resolve_storage_source(source)
        if blob_uri or disk or snapshot:
            snapshot_resource = SubResource(snapshot) if snapshot else None
            managed_disk = SubResource(disk) if disk else None
            return ImageDataDisk(lun,
                                 blob_uri=blob_uri,
                                 snapshot=snapshot_resource,
                                 managed_disk=managed_disk)

    def create_data_disks(self):
        return list(filter(None, [self.create_data_disk(lun, source) for lun, source in enumerate(self.data_disk_sources)]))

    def get_source_vm(self):
        vm_resource_id = format_resource_id(self.source,
                                            self.subscription_id,
                                            'Microsoft.Compute',
                                            'virtualMachines',
                                            self.resource_group)
        resource = parse_resource_id(vm_resource_id)
        return self.get_vm(resource['resource_group'], resource['name']) if resource['type'] == 'virtualMachines' else None

    def get_snapshot(self, snapshot_name):
        return self._get_resource(self.compute_client.snapshots.get, self.resource_group, snapshot_name)

    def get_disk(self, disk_name):
        return self._get_resource(self.compute_client.disks.get, self.resource_group, disk_name)

    def get_vm(self, resource_group, vm_name):
        return self._get_resource(self.compute_client.virtual_machines.get, resource_group, vm_name, 'instanceview')

    def get_image(self):
        return self._get_resource(self.compute_client.images.get, self.resource_group, self.name)
    
    def _get_resource(self, get_method, resource_group, name, expand=None):
        try:
            if expand:
                return get_method(resource_group, name, expand=expand)
            else:
                return get_method(resource_group, name)
        except CloudError as cloud_err:
            # Return None iff the resource is not found
            if cloud_err.status_code == 404:
                self.log('{0}'.format(str(cloud_err)))
                return None
            self.fail('Error: failed to get resource {0} - {1}'.format(name, str(cloud_err)))
        except Exception as exc:
            self.fail('Error: failed to get resource {0} - {1}'.format(name, str(exc)))

    def create_image(self, image):
        try:
            poller = self.compute_client.images.create_or_update(self.resource_group, self.name, image)
            new_image = self.get_poller_result(poller)
        except Exception as exc:
            self.fail("Error creating image {0} - {1}".format(self.name, str(exc)))
        self.check_provisioning_state(new_image)
        return new_image

    def delete_image(self):
        self.log('Deleting image {0}'.format(self.name))
        try:
            poller = self.compute_client.images.delete(self.resource_group, self.name)
            result = self.get_poller_result(poller)
        except Exception as exc:
            self.fail("Error deleting image {0} - {1}".format(self.name, str(exc)))

        return result


def main():
    AzureRMImage()

if __name__ == '__main__':
    main()
