#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Google
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# ----------------------------------------------------------------------------
#
#     ***     AUTO GENERATED CODE    ***    AUTO GENERATED CODE     ***
#
# ----------------------------------------------------------------------------
#
#     This file is automatically generated by Magic Modules and manual
#     changes will be clobbered when the file is regenerated.
#
#     Please read more about how to change this file at
#     https://www.github.com/GoogleCloudPlatform/magic-modules
#
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function

__metaclass__ = type

################################################################################
# Documentation
################################################################################

ANSIBLE_METADATA = {'metadata_version': '1.1', 'status': ["preview"], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: gcp_compute_instance_group_manager_info
description:
- Gather info for GCP InstanceGroupManager
- This module was called C(gcp_compute_instance_group_manager_facts) before Ansible
  2.9. The usage has not changed.
short_description: Gather info for GCP InstanceGroupManager
version_added: '2.7'
author: Google Inc. (@googlecloudplatform)
requirements:
- python >= 2.6
- requests >= 2.18.4
- google-auth >= 1.3.0
options:
  filters:
    description:
    - A list of filter value pairs. Available filters are listed here U(https://cloud.google.com/sdk/gcloud/reference/topic/filters).
    - Each additional filter in the list will act be added as an AND condition (filter1
      and filter2) .
    type: list
  zone:
    description:
    - The zone the managed instance group resides.
    required: true
    type: str
  project:
    description:
    - The Google Cloud Platform project to use.
    type: str
  auth_kind:
    description:
    - The type of credential used.
    type: str
    required: true
    choices:
    - application
    - machineaccount
    - serviceaccount
  service_account_contents:
    description:
    - The contents of a Service Account JSON file, either in a dictionary or as a
      JSON string that represents it.
    type: jsonarg
  service_account_file:
    description:
    - The path of a Service Account JSON file if serviceaccount is selected as type.
    type: path
  service_account_email:
    description:
    - An optional service account email address if machineaccount is selected and
      the user does not wish to use the default email.
    type: str
  scopes:
    description:
    - Array of scopes to be used
    type: list
  env_type:
    description:
    - Specifies which Ansible environment you're running this module within.
    - This should not be set unless you know what you're doing.
    - This only alters the User Agent string for any API requests.
    type: str
notes:
- for authentication, you can set service_account_file using the C(gcp_service_account_file)
  env variable.
- for authentication, you can set service_account_contents using the C(GCP_SERVICE_ACCOUNT_CONTENTS)
  env variable.
- For authentication, you can set service_account_email using the C(GCP_SERVICE_ACCOUNT_EMAIL)
  env variable.
- For authentication, you can set auth_kind using the C(GCP_AUTH_KIND) env variable.
- For authentication, you can set scopes using the C(GCP_SCOPES) env variable.
- Environment variables values will only be used if the playbook values are not set.
- The I(service_account_email) and I(service_account_file) options are mutually exclusive.
'''

EXAMPLES = '''
- name: get info on an instance group manager
  gcp_compute_instance_group_manager_info:
    zone: us-west1-a
    filters:
    - name = test_object
    project: test_project
    auth_kind: serviceaccount
    service_account_file: "/tmp/auth.pem"
'''

RETURN = '''
resources:
  description: List of resources
  returned: always
  type: complex
  contains:
    baseInstanceName:
      description:
      - The base instance name to use for instances in this group. The value must
        be 1-58 characters long. Instances are named by appending a hyphen and a random
        four-character string to the base instance name.
      - The base instance name must comply with RFC1035.
      returned: success
      type: str
    creationTimestamp:
      description:
      - The creation timestamp for this managed instance group in RFC3339 text format.
      returned: success
      type: str
    currentActions:
      description:
      - The list of instance actions and the number of instances in this managed instance
        group that are scheduled for each of those actions.
      returned: success
      type: complex
      contains:
        abandoning:
          description:
          - The total number of instances in the managed instance group that are scheduled
            to be abandoned. Abandoning an instance removes it from the managed instance
            group without deleting it.
          returned: success
          type: int
        creating:
          description:
          - The number of instances in the managed instance group that are scheduled
            to be created or are currently being created. If the group fails to create
            any of these instances, it tries again until it creates the instance successfully.
          - If you have disabled creation retries, this field will not be populated;
            instead, the creatingWithoutRetries field will be populated.
          returned: success
          type: int
        creatingWithoutRetries:
          description:
          - The number of instances that the managed instance group will attempt to
            create. The group attempts to create each instance only once. If the group
            fails to create any of these instances, it decreases the group's targetSize
            value accordingly.
          returned: success
          type: int
        deleting:
          description:
          - The number of instances in the managed instance group that are scheduled
            to be deleted or are currently being deleted.
          returned: success
          type: int
        none:
          description:
          - The number of instances in the managed instance group that are running
            and have no scheduled actions.
          returned: success
          type: int
        recreating:
          description:
          - The number of instances in the managed instance group that are scheduled
            to be recreated or are currently being being recreated.
          - Recreating an instance deletes the existing root persistent disk and creates
            a new disk from the image that is defined in the instance template.
          returned: success
          type: int
        refreshing:
          description:
          - The number of instances in the managed instance group that are being reconfigured
            with properties that do not require a restart or a recreate action. For
            example, setting or removing target pools for the instance.
          returned: success
          type: int
        restarting:
          description:
          - The number of instances in the managed instance group that are scheduled
            to be restarted or are currently being restarted.
          returned: success
          type: int
    description:
      description:
      - An optional description of this resource. Provide this property when you create
        the resource.
      returned: success
      type: str
    id:
      description:
      - A unique identifier for this resource.
      returned: success
      type: int
    instanceGroup:
      description:
      - The instance group being managed.
      returned: success
      type: dict
    instanceTemplate:
      description:
      - The instance template that is specified for this managed instance group. The
        group uses this template to create all new instances in the managed instance
        group.
      returned: success
      type: dict
    name:
      description:
      - The name of the managed instance group. The name must be 1-63 characters long,
        and comply with RFC1035.
      returned: success
      type: str
    namedPorts:
      description:
      - Named ports configured for the Instance Groups complementary to this Instance
        Group Manager.
      returned: success
      type: complex
      contains:
        name:
          description:
          - The name for this named port. The name must be 1-63 characters long, and
            comply with RFC1035.
          returned: success
          type: str
        port:
          description:
          - The port number, which can be a value between 1 and 65535.
          returned: success
          type: int
    region:
      description:
      - The region this managed instance group resides (for regional resources).
      returned: success
      type: str
    targetPools:
      description:
      - TargetPool resources to which instances in the instanceGroup field are added.
        The target pools automatically apply to all of the instances in the managed
        instance group.
      returned: success
      type: list
    targetSize:
      description:
      - The target number of running instances for this managed instance group. Deleting
        or abandoning instances reduces this number. Resizing the group changes this
        number.
      returned: success
      type: int
    zone:
      description:
      - The zone the managed instance group resides.
      returned: success
      type: str
'''

################################################################################
# Imports
################################################################################
from ansible.module_utils.gcp_utils import navigate_hash, GcpSession, GcpModule, GcpRequest
import json

################################################################################
# Main
################################################################################


def main():
    module = GcpModule(argument_spec=dict(filters=dict(type='list', elements='str'), zone=dict(required=True, type='str')))

    if module._name == 'gcp_compute_instance_group_manager_facts':
        module.deprecate("The 'gcp_compute_instance_group_manager_facts' module has been renamed to 'gcp_compute_instance_group_manager_info'", version='2.13')

    if not module.params['scopes']:
        module.params['scopes'] = ['https://www.googleapis.com/auth/compute']

    return_value = {'resources': fetch_list(module, collection(module), query_options(module.params['filters']))}
    module.exit_json(**return_value)


def collection(module):
    return "https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/instanceGroupManagers".format(**module.params)


def fetch_list(module, link, query):
    auth = GcpSession(module, 'compute')
    return auth.list(link, return_if_object, array_name='items', params={'filter': query})


def query_options(filters):
    if not filters:
        return ''

    if len(filters) == 1:
        return filters[0]
    else:
        queries = []
        for f in filters:
            # For multiple queries, all queries should have ()
            if f[0] != '(' and f[-1] != ')':
                queries.append("(%s)" % ''.join(f))
            else:
                queries.append(f)

        return ' '.join(queries)


def return_if_object(module, response):
    # If not found, return nothing.
    if response.status_code == 404:
        return None

    # If no content, return nothing.
    if response.status_code == 204:
        return None

    try:
        module.raise_for_status(response)
        result = response.json()
    except getattr(json.decoder, 'JSONDecodeError', ValueError) as inst:
        module.fail_json(msg="Invalid JSON response with error: %s" % inst)

    if navigate_hash(result, ['error', 'errors']):
        module.fail_json(msg=navigate_hash(result, ['error', 'errors']))

    return result


if __name__ == "__main__":
    main()
