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
module: gcp_compute_autoscaler_info
description:
- Gather info for GCP Autoscaler
short_description: Gather info for GCP Autoscaler
version_added: 2.9
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
    - URL of the zone where the instance group resides.
    required: true
    type: str
extends_documentation_fragment: gcp
'''

EXAMPLES = '''
- name: get info on a autoscaler
  gcp_compute_autoscaler_info:
    zone: us-central1-a
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
    id:
      description:
      - Unique identifier for the resource.
      returned: success
      type: int
    creationTimestamp:
      description:
      - Creation timestamp in RFC3339 text format.
      returned: success
      type: str
    name:
      description:
      - Name of the resource. The name must be 1-63 characters long and match the
        regular expression `[a-z]([-a-z0-9]*[a-z0-9])?` which means the first character
        must be a lowercase letter, and all following characters must be a dash, lowercase
        letter, or digit, except the last character, which cannot be a dash.
      returned: success
      type: str
    description:
      description:
      - An optional description of this resource.
      returned: success
      type: str
    autoscalingPolicy:
      description:
      - 'The configuration parameters for the autoscaling algorithm. You can define
        one or more of the policies for an autoscaler: cpuUtilization, customMetricUtilizations,
        and loadBalancingUtilization.'
      - If none of these are specified, the default will be to autoscale based on
        cpuUtilization to 0.6 or 60%.
      returned: success
      type: complex
      contains:
        minNumReplicas:
          description:
          - The minimum number of replicas that the autoscaler can scale down to.
            This cannot be less than 0. If not provided, autoscaler will choose a
            default value depending on maximum number of instances allowed.
          returned: success
          type: int
        maxNumReplicas:
          description:
          - The maximum number of instances that the autoscaler can scale up to. This
            is required when creating or updating an autoscaler. The maximum number
            of replicas should not be lower than minimal number of replicas.
          returned: success
          type: int
        coolDownPeriodSec:
          description:
          - The number of seconds that the autoscaler should wait before it starts
            collecting information from a new instance. This prevents the autoscaler
            from collecting information when the instance is initializing, during
            which the collected usage would not be reliable. The default time autoscaler
            waits is 60 seconds.
          - Virtual machine initialization times might vary because of numerous factors.
            We recommend that you test how long an instance may take to initialize.
            To do this, create an instance and time the startup process.
          returned: success
          type: int
        cpuUtilization:
          description:
          - Defines the CPU utilization policy that allows the autoscaler to scale
            based on the average CPU utilization of a managed instance group.
          returned: success
          type: complex
          contains:
            utilizationTarget:
              description:
              - The target CPU utilization that the autoscaler should maintain.
              - Must be a float value in the range (0, 1]. If not specified, the default
                is 0.6.
              - If the CPU level is below the target utilization, the autoscaler scales
                down the number of instances until it reaches the minimum number of
                instances you specified or until the average CPU of your instances
                reaches the target utilization.
              - If the average CPU is above the target utilization, the autoscaler
                scales up until it reaches the maximum number of instances you specified
                or until the average utilization reaches the target utilization.
              returned: success
              type: str
        customMetricUtilizations:
          description:
          - Defines the CPU utilization policy that allows the autoscaler to scale
            based on the average CPU utilization of a managed instance group.
          returned: success
          type: complex
          contains:
            metric:
              description:
              - The identifier (type) of the Stackdriver Monitoring metric.
              - The metric cannot have negative values.
              - The metric must have a value type of INT64 or DOUBLE.
              returned: success
              type: str
            utilizationTarget:
              description:
              - The target value of the metric that autoscaler should maintain. This
                must be a positive value. A utilization metric scales number of virtual
                machines handling requests to increase or decrease proportionally
                to the metric.
              - For example, a good metric to use as a utilizationTarget is U(www.googleapis.com/compute/instance/network/received_bytes_count).
              - The autoscaler will work to keep this value constant for each of the
                instances.
              returned: success
              type: str
            utilizationTargetType:
              description:
              - Defines how target utilization value is expressed for a Stackdriver
                Monitoring metric. Either GAUGE, DELTA_PER_SECOND, or DELTA_PER_MINUTE.
              returned: success
              type: str
        loadBalancingUtilization:
          description:
          - Configuration parameters of autoscaling based on a load balancer.
          returned: success
          type: complex
          contains:
            utilizationTarget:
              description:
              - Fraction of backend capacity utilization (set in HTTP(s) load balancing
                configuration) that autoscaler should maintain. Must be a positive
                float value. If not defined, the default is 0.8.
              returned: success
              type: str
    target:
      description:
      - URL of the managed instance group that this autoscaler will scale.
      returned: success
      type: dict
    zone:
      description:
      - URL of the zone where the instance group resides.
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

    if not module.params['scopes']:
        module.params['scopes'] = ['https://www.googleapis.com/auth/compute']

    items = fetch_list(module, collection(module), query_options(module.params['filters']))
    if items.get('items'):
        items = items.get('items')
    else:
        items = []
    return_value = {'resources': items}
    module.exit_json(**return_value)


def collection(module):
    return "https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/autoscalers".format(**module.params)


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
