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

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ["preview"],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: gcp_compute_target_pool_facts
description:
  - Gather facts for GCP TargetPool
short_description: Gather facts for GCP TargetPool
version_added: 2.7
author: Google Inc. (@googlecloudplatform)
requirements:
    - python >= 2.6
    - requests >= 2.18.4
    - google-auth >= 1.3.0
options:
    filters:
       description:
           A list of filter value pairs. Available filters are listed here
           U(https://cloud.google.com/sdk/gcloud/reference/topic/filters).
           Each additional filter in the list will act be added as an AND condition
           (filter1 and filter2)
    region:
        description:
            - The region where the target pool resides.
        required: true
extends_documentation_fragment: gcp
'''

EXAMPLES = '''
- name:  a target pool facts
  gcp_compute_target_pool_facts:
      region: us-west1
      filters:
      - name = test_object
      project: test_project
      auth_kind: serviceaccount
      service_account_file: "/tmp/auth.pem"
'''

RETURN = '''
items:
    description: List of items
    returned: always
    type: complex
    contains:
        backup_pool:
            description:
                - This field is applicable only when the containing target pool is serving a forwarding
                  rule as the primary pool, and its failoverRatio field is properly set to a value
                  between [0, 1].
                - 'backupPool and failoverRatio together define the fallback behavior of the primary
                  target pool: if the ratio of the healthy instances in the primary pool is at or
                  below failoverRatio, traffic arriving at the load-balanced IP will be directed to
                  the backup pool.'
                - In case where failoverRatio and backupPool are not set, or all the instances in
                  the backup pool are unhealthy, the traffic will be directed back to the primary
                  pool in the "force" mode, where traffic will be spread to the healthy instances
                  with the best effort, or to all instances when no instance is healthy.
            returned: success
            type: dict
        creation_timestamp:
            description:
                - Creation timestamp in RFC3339 text format.
            returned: success
            type: str
        description:
            description:
                - An optional description of this resource.
            returned: success
            type: str
        failover_ratio:
            description:
                - This field is applicable only when the containing target pool is serving a forwarding
                  rule as the primary pool (i.e., not as a backup pool to some other target pool).
                  The value of the field must be in [0, 1].
                - 'If set, backupPool must also be set. They together define the fallback behavior
                  of the primary target pool: if the ratio of the healthy instances in the primary
                  pool is at or below this number, traffic arriving at the load-balanced IP will be
                  directed to the backup pool.'
                - In case where failoverRatio is not set or all the instances in the backup pool are
                  unhealthy, the traffic will be directed back to the primary pool in the "force"
                  mode, where traffic will be spread to the healthy instances with the best effort,
                  or to all instances when no instance is healthy.
            returned: success
            type: str
        health_check:
            description:
                - A reference to a HttpHealthCheck resource.
                - A member instance in this pool is considered healthy if and only if the health checks
                  pass. If not specified it means all member instances will be considered healthy
                  at all times.
            returned: success
            type: dict
        id:
            description:
                - The unique identifier for the resource.
            returned: success
            type: int
        instances:
            description:
                - A list of virtual machine instances serving this pool.
                - They must live in zones contained in the same region as this pool.
            returned: success
            type: list
        name:
            description:
                - Name of the resource. Provided by the client when the resource is created. The name
                  must be 1-63 characters long, and comply with RFC1035. Specifically, the name must
                  be 1-63 characters long and match the regular expression `[a-z]([-a-z0-9]*[a-z0-9])?`
                  which means the first character must be a lowercase letter, and all following characters
                  must be a dash, lowercase letter, or digit, except the last character, which cannot
                  be a dash.
            returned: success
            type: str
        session_affinity:
            description:
                - 'Session affinity option. Must be one of these values:  - NONE: Connections from
                  the same client IP may go to any instance in   the pool.'
                - "- CLIENT_IP: Connections from the same client IP will go to the same   instance
                  in the pool while that instance remains healthy."
                - "- CLIENT_IP_PROTO: Connections from the same client IP with the same   IP protocol
                  will go to the same instance in the pool while that   instance remains healthy."
            returned: success
            type: str
        region:
            description:
                - The region where the target pool resides.
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
    module = GcpModule(
        argument_spec=dict(
            filters=dict(type='list', elements='str'),
            region=dict(required=True, type='str')
        )
    )

    if 'scopes' not in module.params:
        module.params['scopes'] = ['https://www.googleapis.com/auth/compute']

    items = fetch_list(module, collection(module), query_options(module.params['filters']))
    if items.get('items'):
        items = items.get('items')
    else:
        items = []
    return_value = {
        'items': items
    }
    module.exit_json(**return_value)


def collection(module):
    return "https://www.googleapis.com/compute/v1/projects/{project}/regions/{region}/targetPools".format(**module.params)


def fetch_list(module, link, query):
    auth = GcpSession(module, 'compute')
    response = auth.get(link, params={'filter': query})
    return return_if_object(module, response)


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
