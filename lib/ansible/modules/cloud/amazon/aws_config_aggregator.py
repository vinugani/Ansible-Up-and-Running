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
module: aws_config_aggregator
short_description: Manage AWS Config aggregations across multiple accounts
description:
    - Module manages AWS Config resources
version_added: "2.6"
requirements: [ 'botocore', 'boto3' ]
author:
    - "Aaron Smith (@slapula)"
options:
  name:
    description:
    - The name of the AWS Config resource.
    required: true
  state:
    description:
    - Whether the Config rule should be present or absent.
    default: present
    choices: ['present', 'absent']
  account_sources:
    description:
    - Provides a list of source accounts and regions to be aggregated.
    suboptions:
      account_ids:
        description:
        - A list of 12-digit account IDs of accounts being aggregated.
      aws_regions:
        description:
        - A list of source regions being aggregated.
      all_aws_regions:
        description:
        - If true, aggreagate existing AWS Config regions and future regions.
  organization_source:
    description:
    - The region authorized to collect aggregated data.
    suboptions:
      role_arn:
        description:
        - ARN of the IAM role used to retreive AWS Organization details associated with the aggregator account.
      aws_regions:
        description:
        - The source regions being aggregated.
      all_aws_regions:
        description:
        - If true, aggreagate existing AWS Config regions and future regions.
extends_documentation_fragment:
  - aws
  - ec2
'''

EXAMPLES = r'''
- name: Create Configuration Recorder for AWS Config
  aws_config:
    name: test_configuration_recorder
    state: present
    resource_type: configuration_recorder
    role_arn: 'arn:aws:iam::123456789012:role/AwsConfigRecorder'
    recording_group:
        all_supported: true
        include_global_types: true

- name: Create Delivery Channel for AWS Config
  aws_config:
    name: test_delivery_channel
    state: present
    resource_type: delivery_channel
    s3_bucket: 'test_aws_config_bucket'
    sns_topic_arn: 'arn:aws:sns:us-east-1:123456789012:aws_config_topic:1234ab56-cdef-7g89-01hi-2jk34l5m67no'
    delivery_frequency: 'Twelve_Hours'

- name: Create Config Rule for AWS Config
  aws_config:
    name: test_config_rule
    state: present
    resource_type: rule
    description: 'This AWS Config rule checks for public write access on S3 buckets'
    scope:
        compliance_types:
            - 'AWS::S3::Bucket'
    source:
        owner: AWS
        identifier: 'S3_BUCKET_PUBLIC_WRITE_PROHIBITED'

'''

RETURN = r'''#'''


try:
    import botocore
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    pass  # handled by AnsibleAWSModule

from ansible.module_utils.aws.core import AnsibleAWSModule
from ansible.module_utils.ec2 import boto3_conn, get_aws_connection_info, AWSRetry
from ansible.module_utils.ec2 import camel_dict_to_snake_dict, boto3_tag_list_to_ansible_dict


def resource_exists(client, module, resource_type, params):
    try:
        aggregator = client.describe_configuration_aggregators(
            ConfigurationAggregatorNames=[params['name']]
        )
        return aggregator['ConfigurationAggregators'][0]
    except client.exceptions.from_code('NoSuchConfigurationAggregatorException'):
        return
    except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError):
        module.fail_json_aws(e)


def create_resource(client, module, params, result):
    try:
        response = client.put_configuration_aggregator(
            ConfigurationAggregatorName=params['ConfigurationAggregatorName'],
            AccountAggregationSources=params['AccountAggregationSources'],
            OrganizationAggregationSource=params['OrganizationAggregationSource']
        )
        result['changed'] = True
        result['aggregator'] = camel_dict_to_snake_dict(resource_exists(client, module, params))
        return result
    except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as e:
        module.fail_json_aws(e, msg="Couldn't create AWS Config configuration aggregator")


def update_resource(client, module, resource_type, params, result):
    current_params = client.describe_configuration_aggregators(
        ConfigurationAggregatorNames=[params['name']]
    )

    del current_params['ConfigurationAggregatorArn']
    del current_params['CreationTime']
    del current_params['LastUpdatedTime']

    if params != current_params['ConfigurationAggregators'][0]:
        try:
            client.put_configuration_aggregator(
                ConfigurationAggregatorName=params['ConfigurationAggregatorName'],
                AccountAggregationSources=params['AccountAggregationSources'],
                OrganizationAggregationSource=params['OrganizationAggregationSource']
            )
            result['changed'] = True
            result['aggregator'] = camel_dict_to_snake_dict(resource_exists(client, module, params))
            return result
        except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as e:
            module.fail_json_aws(e, msg="Couldn't create AWS Config configuration aggregator")


def delete_resource(client, module, resource_type, params, result):
    try:
        client.delete_configuration_aggregator(
            ConfigurationAggregatorName=params['ConfigurationAggregatorName']
        )
        result['changed'] = True
        return result
    except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as e:
        module.fail_json_aws(e, msg="Couldn't delete AWS Config configuration aggregator")


def main():
    module = AnsibleAWSModule(
        argument_spec={
            'name': dict(type='str', required=True),
            'state': dict(type='str', choices=['present', 'absent'], default='present'),
            'account_sources': dict(type='list', required=True),
            'organization_source': dict(type='dict', required=True)
        },
        supports_check_mode=False,
    )

    result = {
        'changed': False
    }

    name = module.params.get('name')
    state = module.params.get('state')

    params = {}
    if name:
        params['ConfigurationAggregatorName'] = name
    if module.params.get('account_sources'):
        params['AccountAggregationSources'] = []
        for i in module.params.get('account_sources'):
            tmp_dict = {}
            if i.get('account_ids'):
                tmp_dict['AccountIds'] = i.get('account_ids')
            if i.get('aws_regions'):
                tmp_dict['AwsRegions'] = i.get('aws_regions')
            if i.get('all_aws_regions') is not None:
                tmp_dict['AllAwsRegions'] = i.get('all_aws_regions')
            params['AccountAggregationSources'].append(tmp_dict)
    if module.params.get('organization_source'):
        params['OrganizationAggregationSource'] = {}
        if module.params.get('organization_source').get('role_arn'):
            params['OrganizationAggregationSource'].update({
                'RoleArn': module.params.get('organization_source').get('role_arn')
            })
        if module.params.get('organization_source').get('aws_regions'):
            params['OrganizationAggregationSource'].update({
                'AwsRegions': module.params.get('organization_source').get('aws_regions')
            })
        if module.params.get('organization_source').get('all_aws_regions') is not None:
            params['OrganizationAggregationSourcep'].update({
                'AllAwsRegions': module.params.get('organization_source').get('all_aws_regions')
            })

    client = module.client('config', retry_decorator=AWSRetry.jittered_backoff())

    resource_status = resource_exists(client, module, params)

    if state == 'present':
        if not resource_status:
            create_resource(client, module, params, result)
        else:
            update_resource(client, module, params, result)

    if state == 'absent':
        if resource_status:
            delete_resource(client, module, params, result)

    module.exit_json(changed=result['changed'])


if __name__ == '__main__':
    main()
