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
module: gcp_runtimeconfig_config
description:
- A RuntimeConfig resource is the primary resource in the Cloud RuntimeConfig service.
- A RuntimeConfig resource consists of metadata and a hierarchy of variables.
short_description: Creates a GCP Config
version_added: '2.10'
author: Google Inc. (@googlecloudplatform)
requirements:
- python >= 2.6
- requests >= 2.18.4
- google-auth >= 1.3.0
options:
  state:
    description:
    - Whether the given object should exist in GCP
    choices:
    - present
    - absent
    default: present
    type: str
  description:
    description:
    - The description to associate with the runtime config.
    required: false
    type: str
  name:
    description:
    - The name of the runtime config.
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
'''

EXAMPLES = '''
- name: create a config
  gcp_runtimeconfig_config:
    name: test_object
    description: My config
    project: test_project
    auth_kind: serviceaccount
    service_account_file: "/tmp/auth.pem"
    state: present
'''

RETURN = '''
description:
  description:
  - The description to associate with the runtime config.
  returned: success
  type: str
name:
  description:
  - The name of the runtime config.
  returned: success
  type: str
'''

################################################################################
# Imports
################################################################################

from ansible.module_utils.gcp_utils import navigate_hash, GcpSession, GcpModule, GcpRequest, replace_resource_dict
import json
import re

################################################################################
# Main
################################################################################


def main():
    """Main function"""

    module = GcpModule(
        argument_spec=dict(
            state=dict(default='present', choices=['present', 'absent'], type='str'), description=dict(type='str'), name=dict(required=True, type='str')
        )
    )

    if not module.params['scopes']:
        module.params['scopes'] = ['https://www.googleapis.com/auth/cloudruntimeconfig']

    state = module.params['state']

    fetch = fetch_resource(module, self_link(module))
    changed = False

    if fetch:
        if state == 'present':
            if is_different(module, fetch):
                update(module, self_link(module))
                fetch = fetch_resource(module, self_link(module))
                changed = True
        else:
            delete(module, self_link(module))
            fetch = {}
            changed = True
    else:
        if state == 'present':
            fetch = create(module, collection(module))
            changed = True
        else:
            fetch = {}

    fetch.update({'changed': changed})

    module.exit_json(**fetch)


def create(module, link):
    auth = GcpSession(module, 'runtimeconfig')
    return return_if_object(module, auth.post(link, resource_to_request(module)))


def update(module, link):
    auth = GcpSession(module, 'runtimeconfig')
    return return_if_object(module, auth.put(link, resource_to_request(module)))


def delete(module, link):
    auth = GcpSession(module, 'runtimeconfig')
    return return_if_object(module, auth.delete(link))


def resource_to_request(module):
    request = {u'name': name_pattern(module.params.get('name'), module), u'description': module.params.get('description')}
    return_vals = {}
    for k, v in request.items():
        if v or v is False:
            return_vals[k] = v

    return return_vals


def fetch_resource(module, link, allow_not_found=True):
    auth = GcpSession(module, 'runtimeconfig')
    return return_if_object(module, auth.get(link), allow_not_found)


def self_link(module):
    return "https://runtimeconfig.googleapis.com/v1beta1/projects/{project}/configs/{name}".format(**module.params)


def collection(module):
    return "https://runtimeconfig.googleapis.com/v1beta1/projects/{project}/configs".format(**module.params)


def return_if_object(module, response, allow_not_found=False):
    # If not found, return nothing.
    if allow_not_found and response.status_code == 404:
        return None

    # If no content, return nothing.
    if response.status_code == 204:
        return None

    try:
        module.raise_for_status(response)
        result = response.json()
    except getattr(json.decoder, 'JSONDecodeError', ValueError):
        module.fail_json(msg="Invalid JSON response with error: %s" % response.text)

    if navigate_hash(result, ['error', 'errors']):
        module.fail_json(msg=navigate_hash(result, ['error', 'errors']))

    return result


def is_different(module, response):
    request = resource_to_request(module)
    response = response_to_hash(module, response)

    # Remove all output-only from response.
    response_vals = {}
    for k, v in response.items():
        if k in request:
            response_vals[k] = v

    request_vals = {}
    for k, v in request.items():
        if k in response:
            request_vals[k] = v

    return GcpRequest(request_vals) != GcpRequest(response_vals)


# Remove unnecessary properties from the response.
# This is for doing comparisons with Ansible's current parameters.
def response_to_hash(module, response):
    return {u'description': response.get(u'description')}


def name_pattern(name, module):
    if name is None:
        return

    regex = r"projects/.*/configs/.*"

    if not re.match(regex, name):
        name = "projects/{project}/configs/{name}".format(**module.params)

    return name


if __name__ == '__main__':
    main()
