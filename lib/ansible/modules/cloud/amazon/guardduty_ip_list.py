#!/usr/bin/python

# Copyright: (c) 2018, Aaron Smith <ajsmith10381@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = r'''
---
module: guardduty_ip_list
short_description: Manage Trusted/Threat IP list for AWS GuardDuty.
description:
    - Manage a Trusted/Threat IP list assigned to a AWS GuardDuty detector.
author: "Aaron Smith (@slapula)"
version_added: "2.7"
requirements: [ 'botocore', 'boto3' ]
options:
  name:
    description:
    - A user-friendly name that is displayed in all finding generated by activity that involves
      IP addresses included in this list.
    required: true
  list_type:
    description:
    - Whether the list should be exist or not on the detector.
    required: true
    choices: ['trusted', 'threat']
  state:
    description:
    - Whether the list should be exist or not on the detector.
    default: 'present'
    choices: ['present', 'absent']
  enabled:
    description:
    - Whether the list should be enabled or disabled.
    type: bool
    default: true
  detector_id:
    description:
    - The unique ID of the detector that you want to update.
    required: true
  format:
    description:
    - The format of the file that contains the IP list.
    choices: ['TXT', 'STIX', 'OTX_CSV', 'ALIEN_VAULT', 'PROOF_POINT', 'FIRE_EYE']
  location:
    description:
    - The URI of the file that contains the IP list.
extends_documentation_fragment:
    - ec2
    - aws
'''


EXAMPLES = r'''
- name: create GuardDuty detector
  guardduty_threatlist:
    state: present
    enabled: true

- name: disable GuardDuty detector
  guardduty_threatlist:
    state: present
    enabled: false

- name: delete GuardDuty detector
  guardduty_threatlist:
    state: absent
'''


RETURN = r'''#'''

import os

from ansible.module_utils.aws.core import AnsibleAWSModule
from ansible.module_utils.ec2 import boto3_conn, get_aws_connection_info, AWSRetry
from ansible.module_utils.ec2 import camel_dict_to_snake_dict, boto3_tag_list_to_ansible_dict

try:
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    pass  # handled by AnsibleAWSModule


def ip_list_exists(client, module, result):
    try:
        if module.params.get('list_type') == 'trusted':
            sets = client.list_ip_sets(
                DetectorId=module.params.get('detector_id')
            )
            for i in sets['IpSetIds']:
                ti_set = client.get_ip_set(
                    DetectorId=module.params.get('detector_id'),
                    IpSetId=i
                )
                if ti_set['Name'] == module.params.get('name'):
                    result['trusted_set_id'] = i
                    return True
        if module.params.get('list_type') == 'threat':
            sets = client.list_threat_intel_sets(
                DetectorId=module.params.get('detector_id')
            )
            for i in sets['ThreatIntelSetIds']:
                ti_set = client.get_threat_intel_set(
                    DetectorId=module.params.get('detector_id'),
                    ThreatIntelSetId=i
                )
                if ti_set['Name'] == module.params.get('name'):
                    result['threat_set_id'] = i
                    return True
    except ClientError:
        return False

    return False


def create_ip_list(client, module, params, result):
    if module.check_mode:
        module.exit_json(changed=True)
    try:
        if module.params.get('list_type') == 'trusted':
            response = client.create_ip_set(**params)
            result['trusted_set_id'] = response['IpSetId']
            result['changed'] = True
            return result
        if module.params.get('list_type') == 'threat':
            response = client.create_threat_intel_set(**params)
            result['threat_set_id'] = response['ThreatIntelSetId']
            result['changed'] = True
            return result
    except (BotoCoreError, ClientError) as e:
        module.fail_json_aws(e, msg="Failed to create IP list")

    return result


def update_ip_list(client, module, params, result):
    if module.check_mode:
        module.exit_json(changed=True)
    try:
        if module.params.get('list_type') == 'trusted':
            params['IpSetId'] = result['trusted_set_id']
            del params['Format']
            response = client.update_ip_set(**params)
            result['changed'] = True
            return result
        if module.params.get('list_type') == 'threat':
            params['ThreatIntelSetId'] = result['threat_set_id']
            del params['Format']
            response = client.update_threat_intel_set(**params)
            result['changed'] = True
            return result
    except (BotoCoreError, ClientError) as e:
        module.fail_json_aws(e, msg="Failed to update IP list")

    return result


def delete_ip_list(client, module, result):
    if module.check_mode:
        module.exit_json(changed=True)
    try:
        if module.params.get('list_type') == 'trusted':
            response = client.delete_ip_set(
                DetectorId=module.params.get('detector_id'),
                IpSetId=result['trusted_set_id']
            )
            result['changed'] = True
            return result
        if module.params.get('list_type') == 'threat':
            response = client.delete_threat_intel_set(
                DetectorId=module.params.get('detector_id'),
                ThreatIntelSetId=result['threat_set_id']
            )
            result['changed'] = True
            return result
    except (BotoCoreError, ClientError) as e:
        module.fail_json_aws(e, msg="Failed to delete IP list")

    return result


def main():
    module = AnsibleAWSModule(
        argument_spec={
            'name': dict(type='str', required=True),
            'list_type': dict(type='str', choices=['trusted', 'threat'], required=True),
            'state': dict(type='str', choices=['present', 'absent'], default='present'),
            'enabled': dict(type='bool', default=True),
            'detector_id': dict(type='str', required=True),
            'format': dict(type='str', choices=['TXT', 'STIX', 'OTX_CSV', 'ALIEN_VAULT', 'PROOF_POINT', 'FIRE_EYE']),
            'location': dict(type='str', required=True),
        },
        supports_check_mode=True,
    )

    result = {
        'changed': False
    }

    desired_state = module.params.get('state')

    client = module.client('guardduty')

    ip_list_status = ip_list_exists(client, module, result)

    params = {}
    params['Name'] = module.params.get('name')
    params['Location'] = module.params.get('location')
    params['Format'] = module.params.get('format')
    params['DetectorId'] = module.params.get('detector_id')
    params['Activate'] = module.params.get('enabled')

    if desired_state == 'present':
        if not ip_list_status:
            create_ip_list(client, module, params, result)
        if ip_list_status:
            update_ip_list(client, module, params, result)

    if desired_state == 'absent':
        if ip_list_status:
            delete_ip_list(client, module, result)

    module.exit_json(changed=result['changed'], results=result)


if __name__ == '__main__':
    main()
