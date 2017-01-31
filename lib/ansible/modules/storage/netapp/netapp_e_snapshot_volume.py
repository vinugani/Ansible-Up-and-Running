#!/usr/bin/python

# (c) 2016, NetApp, Inc
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
ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = """
---
module: netapp_e_snapshot_volume
short_description: Manage E/EF-Series snapshot volumes.
description:
    - Create, update, remove snapshot volumes for NetApp E/EF-Series storage arrays.
version_added: '2.2'
author: Kevin Hulquest (@hulquest)
note: Only I(full_threshold) is supported for update operations. If the snapshot volume already exists and the threshold matches, then an C(ok) status will be returned, no other changes can be made to a pre-existing snapshot volume.
extends_documentation_fragment:
    - netapp.eseries
options:
    snapshot_image_id:
      required: True
      description:
          - The identifier of the snapshot image used to create the new snapshot volume.
          - "Note: You'll likely want to use the M(netapp_e_facts) module to find the ID of the image you want."
    full_threshold:
      description:
          - The repository utilization warning threshold percentage
      default: 85
    name:
      required: True
      description:
          - The name you wish to give the snapshot volume
    view_mode:
      required: True
      description:
          - The snapshot volume access mode
      choices:
          - modeUnknown
          - readWrite
          - readOnly
          - __UNDEFINED
    repo_percentage:
      description:
          - The size of the view in relation to the size of the base volume
      default: 20
    storage_pool_name:
      description:
          - Name of the storage pool on which to allocate the repository volume.
      required: True
    state:
      description:
          - Whether to create or remove the snapshot volume
      required: True
      choices:
          - absent
          - present
"""
EXAMPLES = """
    - name: Snapshot volume
      netapp_e_snapshot_volume:
        ssid: "{{ ssid }}"
        api_url: "{{ netapp_api_url }}"/
        api_username: "{{ netapp_api_username }}"
        api_password: "{{ netapp_api_password }}"
        state: present
        storage_pool_name: "{{ snapshot_volume_storage_pool_name }}"
        snapshot_image_id: "{{ snapshot_volume_image_id }}"
        name: "{{ snapshot_volume_name }}"
"""
RETURN = """
msg:
    description: Success message
    returned: success
    type: string
    sample: Json facts for the volume that was created.
"""
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}
import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.netapp import request, eseries_host_argument_spec


class SnapshotVolume(object):
    def __init__(self):
        argument_spec = eseries_host_argument_spec()
        argument_spec.update(dict(
            snapshot_image_id=dict(type='str', required=True),
            full_threshold=dict(type='int', default=85),
            name=dict(type='str', required=True),
            view_mode=dict(type='str', default='readOnly',
                           choices=['readOnly', 'readWrite', 'modeUnknown', '__Undefined']),
            repo_percentage=dict(type='int', default=20),
            storage_pool_name=dict(type='str', required=True),
            state=dict(type='str', required=True, choices=['absent', 'present'])
        ))

        self.module = AnsibleModule(argument_spec=argument_spec)
        args = self.module.params
        self.state = args['state']
        self.ssid = args['ssid']
        self.snapshot_image_id = args['snapshot_image_id']
        self.full_threshold = args['full_threshold']
        self.name = args['name']
        self.view_mode = args['view_mode']
        self.repo_percentage = args['repo_percentage']
        self.storage_pool_name = args['storage_pool_name']
        self.url = args['api_url']
        self.user = args['api_username']
        self.pwd = args['api_password']
        self.certs = args['validate_certs']

        if not self.url.endswith('/'):
            self.url += '/'

    @property
    def pool_id(self):
        pools = 'storage-systems/%s/storage-pools' % self.ssid
        url = self.url + pools
        (rc, data) = request(url, headers=HEADERS, url_username=self.user, url_password=self.pwd,
                             validate_certs=self.certs)

        for pool in data:
            if pool['name'] == self.storage_pool_name:
                self.pool_data = pool
                return pool['id']

        self.module.fail_json(msg="No storage pool with the name: '%s' was found" % self.name)

    @property
    def ss_vol_exists(self):
        rc, ss_vols = request(self.url + 'storage-systems/%s/snapshot-volumes' % self.ssid, headers=HEADERS,
                              url_username=self.user, url_password=self.pwd, validate_certs=self.certs)
        if ss_vols:
            for ss_vol in ss_vols:
                if ss_vol['name'] == self.name:
                    self.ss_vol = ss_vol
                    return True
        else:
            return False

        return False

    @property
    def ss_vol_needs_update(self):
        if self.ss_vol['fullWarnThreshold'] != self.full_threshold:
            return True
        else:
            return False

    def create_ss_vol(self):
        post_data = dict(
            snapshotImageId=self.snapshot_image_id,
            fullThreshold=self.full_threshold,
            name=self.name,
            viewMode=self.view_mode,
            repositoryPercentage=self.repo_percentage,
            repositoryPoolId=self.pool_id
        )

        rc, create_resp = request(self.url + 'storage-systems/%s/snapshot-volumes' % self.ssid,
                                  data=json.dumps(post_data), headers=HEADERS, url_username=self.user,
                                  url_password=self.pwd, validate_certs=self.certs, method='POST')

        self.ss_vol = create_resp
        # Doing a check after creation because the creation call fails to set the specified warning threshold
        if self.ss_vol_needs_update:
            self.update_ss_vol()
        else:
            self.module.exit_json(changed=True, **create_resp)

    def update_ss_vol(self):
        post_data = dict(
            fullThreshold=self.full_threshold,
        )

        rc, resp = request(self.url + 'storage-systems/%s/snapshot-volumes/%s' % (self.ssid, self.ss_vol['id']),
                           data=json.dumps(post_data), headers=HEADERS, url_username=self.user, url_password=self.pwd,
                           method='POST', validate_certs=self.certs)

        self.module.exit_json(changed=True, **resp)

    def remove_ss_vol(self):
        rc, resp = request(self.url + 'storage-systems/%s/snapshot-volumes/%s' % (self.ssid, self.ss_vol['id']),
                           headers=HEADERS, url_username=self.user, url_password=self.pwd, validate_certs=self.certs,
                           method='DELETE')
        self.module.exit_json(changed=True, msg="Volume successfully deleted")

    def apply(self):
        if self.state == 'present':
            if self.ss_vol_exists:
                if self.ss_vol_needs_update:
                    self.update_ss_vol()
                else:
                    self.module.exit_json(changed=False, **self.ss_vol)
            else:
                self.create_ss_vol()
        else:
            if self.ss_vol_exists:
                self.remove_ss_vol()
            else:
                self.module.exit_json(changed=False, msg="Volume already absent")


def main():
    sv = SnapshotVolume()
    sv.apply()


if __name__ == '__main__':
    main()
