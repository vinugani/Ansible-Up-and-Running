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
module: gcp_compute_route_facts
description:
- Gather facts for GCP Route
short_description: Gather facts for GCP Route
version_added: 2.7
author: Google Inc. (@googlecloudplatform)
requirements:
- python >= 2.6
- requests >= 2.18.4
- google-auth >= 1.3.0
options:
  filters:
    description:
    - A list of filter value pairs. Available filters are listed here U(https://cloud.google.com/sdk/gcloud/reference/topic/filters.)
    - Each additional filter in the list will act be added as an AND condition (filter1
      and filter2) .
extends_documentation_fragment: gcp
'''

EXAMPLES = '''
- name: " a route facts"
  gcp_compute_route_facts:
    filters:
    - name = test_object
    project: test_project
    auth_kind: serviceaccount
    service_account_file: "/tmp/auth.pem"
    state: facts
'''

RETURN = '''
items:
  description: List of items
  returned: always
  type: complex
  contains:
    destRange:
      description:
      - The destination range of outgoing packets that this route applies to.
      - Only IPv4 is supported.
      returned: success
      type: str
    description:
      description:
      - An optional description of this resource. Provide this property when you create
        the resource.
      returned: success
      type: str
    name:
      description:
      - Name of the resource. Provided by the client when the resource is created.
        The name must be 1-63 characters long, and comply with RFC1035. Specifically,
        the name must be 1-63 characters long and match the regular expression `[a-z]([-a-z0-9]*[a-z0-9])?`
        which means the first character must be a lowercase letter, and all following
        characters must be a dash, lowercase letter, or digit, except the last character,
        which cannot be a dash.
      returned: success
      type: str
    network:
      description:
      - The network that this route applies to.
      returned: success
      type: dict
    priority:
      description:
      - The priority of this route. Priority is used to break ties in cases where
        there is more than one matching route of equal prefix length.
      - In the case of two routes with equal prefix length, the one with the lowest-numbered
        priority value wins.
      - Default value is 1000. Valid range is 0 through 65535.
      returned: success
      type: int
    tags:
      description:
      - A list of instance tags to which this route applies.
      returned: success
      type: list
    nextHopGateway:
      description:
      - URL to a gateway that should handle matching packets.
      - 'Currently, you can only specify the internet gateway, using a full or partial
        valid URL: * U(https://www.googleapis.com/compute/v1/projects/project/global/gateways/default-internet-gateway)
        * projects/project/global/gateways/default-internet-gateway * global/gateways/default-internet-gateway
        .'
      returned: success
      type: str
    nextHopInstance:
      description:
      - URL to an instance that should handle matching packets.
      - 'You can specify this as a full or partial URL. For example: * U(https://www.googleapis.com/compute/v1/projects/project/zones/zone/)
        instances/instance * projects/project/zones/zone/instances/instance * zones/zone/instances/instance
        .'
      returned: success
      type: dict
    nextHopIp:
      description:
      - Network IP address of an instance that should handle matching packets.
      returned: success
      type: str
    nextHopVpnTunnel:
      description:
      - URL to a VpnTunnel that should handle matching packets.
      returned: success
      type: dict
    nextHopNetwork:
      description:
      - URL to a Network that should handle matching packets.
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
    module = GcpModule(argument_spec=dict(filters=dict(type='list', elements='str')))

    if not module.params['scopes']:
        module.params['scopes'] = ['https://www.googleapis.com/auth/compute']

    items = fetch_list(module, collection(module), query_options(module.params['filters']))
    if items.get('items'):
        items = items.get('items')
    else:
        items = []
    return_value = {'items': items}
    module.exit_json(**return_value)


def collection(module):
    return "https://www.googleapis.com/compute/v1/projects/{project}/global/routes".format(**module.params)


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
