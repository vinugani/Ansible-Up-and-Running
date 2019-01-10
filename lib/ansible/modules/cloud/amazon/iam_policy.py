#!/usr/bin/python
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
ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stableinterface'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: iam_policy
short_description: Manage IAM policies for users, groups, and roles
description:
     - Allows uploading or removing IAM policies for IAM users, groups or roles.
version_added: "2.0"
options:
  iam_type:
    description:
      - Type of IAM resource
    required: true
    choices: [ "user", "group", "role"]
  iam_name:
    description:
      - Name of IAM resource you wish to target for policy actions. In other words, the user name, group name or role name.
    required: true
  policy_name:
    description:
      - The name label for the policy to create or remove.
    required: true
  policy_document:
    description:
      - The path to the properly json formatted policy file (mutually exclusive with C(policy_json))
  policy_json:
    description:
      - A properly json formatted policy as string (mutually exclusive with C(policy_document),
        see https://github.com/ansible/ansible/issues/7005#issuecomment-42894813 on how to use it properly)
  state:
    description:
      - Whether to create or delete the IAM policy.
    choices: [ "present", "absent"]
    default: present
  skip_duplicates:
    description:
      - By default the module looks for any policies that match the document you pass in, if there is a match it will not make a new policy object with
        the same rules. You can override this by specifying false which would allow for two policy objects with different names but same rules.
    default: "/"

notes:
  - 'Currently boto does not support the removal of Managed Policies, the module will not work removing/adding managed policies.'
author:
  - "Jonathan I. Davila (@defionscode)"
  - "Dennis Podkovyrin (@sbj-ss)"
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Create a policy with the name of 'Admin' to the group 'administrators'
- name: Assign a policy called Admin to the administrators group
  iam_policy:
    iam_type: group
    iam_name: administrators
    policy_name: Admin
    state: present
    policy_document: admin_policy.json

# Advanced example, create two new groups and add a READ-ONLY policy to both
# groups.
- name: Create Two Groups, Mario and Luigi
  iam:
    iam_type: group
    name: "{{ item }}"
    state: present
  loop:
     - Mario
     - Luigi
  register: new_groups

- name: Apply READ-ONLY policy to new groups that have been recently created
  iam_policy:
    iam_type: group
    iam_name: "{{ item.created_group.group_name }}"
    policy_name: "READ-ONLY"
    policy_document: readonlypolicy.json
    state: present
  loop: "{{ new_groups.results }}"

# Create a new S3 policy with prefix per user
- name: Create S3 policy from template
  iam_policy:
    iam_type: user
    iam_name: "{{ item.user }}"
    policy_name: "s3_limited_access_{{ item.prefix }}"
    state: present
    policy_json: " {{ lookup( 'template', 's3_policy.json.j2') }} "
    loop:
      - user: s3_user
        prefix: s3_user_prefix

'''
import json

try:
    from botocore.exceptions import BotoCoreError, ClientError, ParamValidationError
except ImportError:
    pass

from ansible.module_utils.aws.core import AnsibleAWSModule
from ansible.module_utils.six import string_types


class PolicyError(Exception):
    pass


class Policy:

    def __init__(self, client, name, policy_name, policy_document, policy_json, skip_duplicates, state, check_mode):
        self.client = client
        self.name = name
        self.policy_name = policy_name
        self.policy_document = policy_document
        self.policy_json = policy_json
        self.skip_duplicates = skip_duplicates
        self.state = state
        self.check_mode = check_mode
        self.changed = False

    @staticmethod
    def _iam_type():
        return ''

    def _list(self, name):
        return {}

    def list(self):
        return self._list(self.name).get('PolicyNames', [])

    def _get(self, name, policy_name):
        return '{}'

    def get(self, policy_name):
        return json.dumps(self._get(self.name, policy_name)['PolicyDocument'], sort_keys=True)

    def _put(self, name, policy_name, policy_doc):
        pass

    def put(self, policy_doc):
        if not self.check_mode:
            self._put(self.name, self.policy_name, policy_doc)
        self.changed = True

    def _delete(self, name, policy_name):
        pass

    def delete(self):
        self.changed = True
        if not self.check_mode:
            try:
                self._delete(self.name, self.policy_name)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    self.changed = False
                else:
                    raise

    def get_policy_text(self):
        if self.policy_document is not None:
            return self.get_policy_from_document()
        if self.policy_json is not None:
            return self.get_policy_from_json()
        return None

    def get_policy_from_document(self):
        try:
            with open(self.policy_document, 'r') as json_data:
                pdoc = json.dumps(json.load(json_data), sort_keys=True)
                json_data.close()
        except IOError as e:
            if e.errno == 2:
                raise PolicyError('policy_document {0:!r} does not exist'.format(self.policy_document))
        return pdoc

    def get_policy_from_json(self):
        try:
            if isinstance(self.policy_json, string_types):
                pdoc = json.dumps(json.loads(self.policy_json), sort_keys=True)
            else:
                pdoc = json.dumps(self.policy_json, sort_keys=True)
        except Exception as e:
            raise PolicyError('Failed to convert the policy into valid JSON: %s' % str(e))
        return pdoc

    def create(self):
        matching_policies = []
        policy_doc = self.get_policy_text()
        for pol in self.list():
            if self.get(pol) == policy_doc:
                matching_policies.append(pol)

        if self.policy_name not in matching_policies or not self.skip_duplicates:
            self.put(policy_doc)

    def run(self):
        if self.state == 'present':
            self.create()
        elif self.state == 'absent':
            self.delete()
        return {
            'changed': self.changed,
            self._iam_type() + '_name': self.name,
            'policies': self.list()
        }


class UserPolicy(Policy):

    @staticmethod
    def _iam_type():
        return 'user'

    def _list(self, name):
        return self.client.list_user_policies(UserName=name)

    def _get(self, name, policy_name):
        return self.client.get_user_policy(UserName=name, PolicyName=policy_name)

    def _put(self, name, policy_name, policy_doc):
        return self.client.put_user_policy(UserName=name, PolicyName=policy_name, PolicyDocument=policy_doc)

    def _delete(self, name, policy_name):
        return self.client.delete_user_policy(UserName=name, PolicyName=policy_name)


class RolePolicy(Policy):

    @staticmethod
    def _iam_type():
        return 'role'

    def _list(self, name):
        return self.client.list_role_policies(RoleName=name)

    def _get(self, name, policy_name):
        return self.client.get_role_policy(RoleName=name, PolicyName=policy_name)

    def _put(self, name, policy_name, policy_doc):
        return self.client.put_role_policy(RoleName=name, PolicyName=policy_name, PolicyDocument=policy_doc)

    def _delete(self, name, policy_name):
        return self.client.delete_role_policy(RoleName=name, PolicyName=policy_name)


class GroupPolicy(Policy):

    @staticmethod
    def _iam_type():
        return 'group'

    def _list(self, name):
        return self.client.list_group_policies(GroupName=name)

    def _get(self, name, policy_name):
        return self.client.get_group_policy(GroupName=name, PolicyName=policy_name)

    def _put(self, name, policy_name, policy_doc):
        return self.client.put_group_policy(GroupName=name, PolicyName=policy_name, PolicyDocument=policy_doc)

    def _delete(self, name, policy_name):
        return self.client.delete_group_policy(GroupName=name, PolicyName=policy_name)


def main():
    argument_spec = dict(
        iam_type=dict(default=None, required=True, choices=['user', 'group', 'role']),
        state=dict(default='present', choices=['present', 'absent']),
        iam_name=dict(default=None, required=False),
        policy_name=dict(default=None, required=True),
        policy_document=dict(default=None, required=False),
        policy_json=dict(type='json', default=None, required=False),
        skip_duplicates=dict(type='bool', default=True, required=False)
    )
    mutually_exclusive = [['policy_document', 'policy_json']]

    module = AnsibleAWSModule(argument_spec=argument_spec, mutually_exclusive=mutually_exclusive, supports_check_mode=True)

    args = dict(
        client=module.client('iam'),
        name=module.params.get('iam_name'),
        policy_name=module.params.get('policy_name'),
        policy_document=module.params.get('policy_document'),
        policy_json=module.params.get('policy_json'),
        skip_duplicates=module.params.get('skip_duplicates'),
        state=module.params.get('state'),
        check_mode=module.check_mode,
    )
    iam_type = module.params.get('iam_type')

    try:
        if iam_type == 'user':
            policy = UserPolicy(**args)
        elif iam_type == 'role':
            policy = RolePolicy(**args)
        elif iam_type == 'group':
            policy = RolePolicy(**args)

        module.exit_json(**(policy.run()))
    except (BotoCoreError, ClientError, ParamValidationError) as e:
        module.fail_json_aws(e)
    except PolicyError as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
