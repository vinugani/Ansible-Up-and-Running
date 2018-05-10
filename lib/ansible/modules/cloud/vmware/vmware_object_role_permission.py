#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Derek Rushing <derek.rushing@geekops.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: vmware_object_role_permission
short_description: Manage object permissions on an ESXi host
description:
    - Manage local roles on an ESXi host
version_added: "2.5"
author:
- Derek Rushing (@kryptsi) <drush@kryptsi.com>
notes:
    - Tested on ESXi 6.5
    - Be sure that the ESXi user used for login, has the appropriate rights to administer permissions
requirements:
    - "python >= 2.7"
    - PyVmomi
options:
    role:
        description:
            - The role to be assigned permission.
        required: True
    principal:
        description:
            - The user to be assigned permission.
        required: False
    group:
        description:
            - The group to be assigned permission.
        required: False
    object_name:
        description:
            - The object name to assigned permission.
        required: True
    object_type:
        description:
            - The object type being targeted.
        required: False
        default: 'Folder'
        choices: ['Folder', 'VirtualMachine', 'Datacenter', 'ResourcePool', 'Datastore', 'Network', 'HostSystem']
    recursive:
        description:
            - Should the permissions be recursively applied.
        required: False
        default: True
    state:
        description:
            - Indicate desired state of the object's permission.
            - If the permission already exists when C(state=present), nothing is changed.
        choices: ['present', 'absent']
        default: present
extends_documentation_fragment: vmware.documentation
'''

EXAMPLES = '''
# Example vmware_object_permission command from Ansible Playbooks
- name: Assign user to VM folder
  vmware_object_role_permission:
      role: administrator
      principal: user_bob
      object_name: services
      state: present

- name: Remove user from VM folder
  vmware_object_role_permission:
      role: administrator
      principal: user_bob
      object_name: services
      state: absent

- name: Assign finance group to VM folder
  vmware_object_role_permission:
      role: Limited Users
      group: finance
      object_name: Accounts
      state: present

'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.vmware import (PyVmomi, vmware_argument_spec,
                                         find_obj, connect_to_api, 
                                         wait_for_task)


class VMwareObjectRolePermission(PyVmomi):
    def __init__(self, module):
        super(VMwareObjectRolePermission, self).__init__(module)
        self.module = module
        self.params = module.params
        self.content = connect_to_api(module)

        if self.params['principal'] is not None:
            self.applied_to = self.params['principal']
            self.is_group = False
        elif self.params['group'] is not None:
            self.applied_to = self.params['group']
            self.is_group = True

        self.get_role()
        self.get_object()
        self.get_perms()
        self.perm = self.setup_permission()
        self.state = self.params['state']

    def get_perms(self):
        self.current_perms = self.content.authorizationManager.RetrieveEntityPermissions(self.current_obj, False)

    def same_permission(self, perm_one, perm_two):
        return perm_one.principal.lower() == perm_two.principal.lower() \
               and perm_one.roleId == perm_two.roleId

    def get_state(self):
        for perm in self.current_perms:
            if self.same_permission(self.perm, perm):
                return 'present'
        return 'absent'

    def process_state(self):
        local_role_manager_states = {
            'absent': {
                'present': self.remove_permission,
                'absent': self.state_exit_unchanged,
            },
            'present': {
                'present': self.state_exit_unchanged,
                'absent': self.add_permission,
            }
        }
        try:
            local_role_manager_states[self.state][self.get_state()]()
        except vmodl.RuntimeFault as runtime_fault:
            self.module.fail_json(msg=runtime_fault.msg)
        except vmodl.MethodFault as method_fault:
            self.module.fail_json(msg=method_fault.msg)
        except Exception as e:
            self.module.fail_json(msg=str(e))

    def state_exit_unchanged(self):
        self.module.exit_json(changed=False)

    def setup_permission(self):
        perm = vim.AuthorizationManager.Permission()
        perm.entity = self.current_obj
        perm.group = self.is_group
        perm.principal = self.applied_to
        perm.roleId = self.role.roleId
        perm.propagate = self.params['recursive']
        return perm

    def add_permission(self):
        self.content.authorizationManager.SetEntityPermissions(self.current_obj, [self.perm])
        self.module.exit_json(changed=True)

    def remove_permission(self):
        self.content.authorizationManager.RemoveEntityPermission(self.current_obj, self.applied_to, self.is_group)
        self.module.exit_json(changed=True)

    def get_role(self):
        for role in self.content.authorizationManager.roleList:
            if role.name == self.params['role']:
                self.role = role
                return
        self.module.fail_json(msg="Specified role ({}) was not found".format(self.params['role']))

    def get_object(self):
        try:
            object_type = getattr(vim, self.params['object_type'])
        except AttributeError:
            self.module.fail_json(msg="Object type {} is not valid.".format(self.params['object_type']))  

        self.current_obj = find_obj(content=self.content, 
            vimtype=[getattr(vim, self.params['object_type'])],
            name=self.params['object_name'])

        if self.current_obj is None:
            self.module.fail_json(msg="Specified object {} of type {} was not found.".format(self.params['object_name'],
                                                                                         self.params['object_type']))


def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(dict(role=dict(required=True, type='str'),
                              object_name=dict(required=True, type='str'),
                              object_type=dict(required=False, type='str', default='Folder',
                                               choices=['Folder', 'VirtualMachine', 'Datacenter',
                                                        'ResourcePool', 'Datastore', 'Network', 
                                                        'HostSystem', 'cluster', 
                                                        'ClusterComputeResource', 
                                                        # 'DistributedVirtualPort',
                                                        'DistributedVirtualSwitch']),
                              principal=dict(required=False, type='str'),
                              group=dict(required=False, type='str'),
                              recursive=dict(required=False, type='bool', default=True),
                              state=dict(default='present', choices=['present', 'absent'], type='str')))

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False,
                           mutually_exclusive=[
                               ['principal', 'group'],
                           ])

    vmware_object_permission = VMwareObjectRolePermission(module)
    vmware_object_permission.process_state()


if __name__ == '__main__':
    main()
