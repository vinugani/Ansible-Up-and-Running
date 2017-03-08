#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Red Hat, Inc.
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

DOCUMENTATION = '''
---
module: ovirt_tags
short_description: Module to manage tags in oVirt
version_added: "2.3"
author: "Ondra Machacek (@machacekondra)"
description:
    - "This module manage tags in oVirt. It can also manage assignments
       of those tags to entities."
options:
    name:
        description:
            - "Name of the the tag to manage."
        required: true
    state:
        description:
            - "Should the tag be present or absent."
        choices: ['present', 'absent']
        default: present
    description:
        description:
            - "Description of the the tag to manage."
    parent:
        description:
            - "Name of the parent tag."
    vms:
        description:
            - "List of the VMs names, which should have assigned this tag."
extends_documentation_fragment: ovirt
'''

EXAMPLES = '''
# Examples don't contain auth parameter for simplicity,
# look at ovirt_auth module to see how to reuse authentication:

# Create(if not exists) and assign tag to vms vm1 and vm2:
- ovirt_tags:
    name: mytag
    vms:
      - vm1
      - vm2

# To detach all VMs from tag:
- ovirt_tags:
    name: mytag
    vms: []

# Remove tag
- ovirt_tags:
    state: absent
    name: mytag
'''

RETURN = '''
id:
    description: ID of the tag which is managed
    returned: On success if tag is found.
    type: str
    sample: 7de90f31-222c-436c-a1ca-7e655bd5b60c
tag:
    description: "Dictionary of all the tag attributes. Tag attributes can be found on your oVirt instance
                  at following url: https://ovirt.example.com/ovirt-engine/api/model#types/tag."
    returned: On success if tag is found.
'''

import traceback

try:
    import ovirtsdk4.types as otypes
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ovirt import (
    BaseModule,
    check_sdk,
    create_connection,
    equal,
    ovirt_full_argument_spec,
    search_by_name,
)


class TagsModule(BaseModule):

    def build_entity(self):
        return otypes.Tag(
            name=self._module.params['name'],
            description=self._module.params['description'],
            parent=otypes.Tag(
                name=self._module.params['parent'],
            ) if self._module.params['parent'] else None,
        )

    def post_create(self, entity):
        self.update_check(entity)

    def _update_tag_assignments(self, entity, name):
        if self._module.params[name] is None:
            return

        entities_service = getattr(self._connection.system_service(), '%s_service' % name)()
        current_vms = [
            vm.name
            for vm in entities_service.list(search='tag=%s' % self._module.params['name'])
        ]
        # Assign tags:
        for entity_name in self._module.params[name]:
            entity = search_by_name(entities_service, entity_name)
            tags_service = entities_service.service(entity.id).tags_service()
            current_tags = [tag.name for tag in tags_service.list()]
            # Assign the tag:
            if self._module.params['name'] not in current_tags:
                if not self._module.check_mode:
                    tags_service.add(
                        tag=otypes.Tag(
                            name=self._module.params['name'],
                        ),
                    )
                self.changed = True

        # Unassign tags:
        for entity_name in [e for e in current_vms if e not in self._module.params[name]]:
            if not self._module.check_mode:
                entity = search_by_name(entities_service, entity_name)
                tags_service = entities_service.service(entity.id).tags_service()
                tag_id = [tag.id for tag in tags_service.list() if tag.name == self._module.params['name']][0]
                tags_service.tag_service(tag_id).remove()
            self.changed = True

    def _get_parent(self, entity):
        parent = None
        if entity.parent:
            parent = self._connection.follow_link(entity.parent).name
        return parent

    def update_check(self, entity):
        self._update_tag_assignments(entity, 'vms')
        self._update_tag_assignments(entity, 'hosts')
        return (
            equal(self._module.params.get('description'), entity.description) and
            equal(self._module.params.get('parent'), self._get_parent(entity))
        )


def main():
    argument_spec = ovirt_full_argument_spec(
        state=dict(
            choices=['present', 'absent'],
            default='present',
        ),
        name=dict(default=None, required=True),
        description=dict(default=None),
        parent=dict(default=None),
        vms=dict(default=None, type='list'),
        hosts=dict(default=None, type='list'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    check_sdk(module)

    try:
        auth = module.params.pop('auth')
        connection = create_connection(auth)
        tags_service = connection.system_service().tags_service()
        tags_module = TagsModule(
            connection=connection,
            module=module,
            service=tags_service,
        )

        state = module.params['state']
        if state == 'present':
            ret = tags_module.create()
        elif state == 'absent':
            ret = tags_module.remove()

        module.exit_json(**ret)
    except Exception as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc())
    finally:
        connection.close(logout=auth.get('token') is None)


if __name__ == "__main__":
    main()
