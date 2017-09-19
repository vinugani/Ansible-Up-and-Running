#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stableinterface'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
---
module: ec2_vpc_nacl_facts
short_description: Gather facts about Network ACLs in an AWS VPC
description:
    - Gather facts about Network ACLs in an AWS VPC
version_added: "2.2"
author: "Brad Davidson (@brandond)"
requirements: [ boto3 ]
options:
  nacl_ids:
    description:
      - A list of Network ACL IDs to retrieve facts about.
    required: false
    default: []
    aliases: [nacl_id]
  filters:
    description:
      - A dict of filters to apply. Each dict item consists of a filter key and a filter value. See \
      U(http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeNetworkAcls.html) for possible filters. Filter \
      names and values are case sensitive.
    required: false
    default: {}
notes:
  - By default, the module will return all Network ACLs.

extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Note: These examples do not set authentication details, see the AWS Guide for details.

# Gather facts about all Network ACLs:
- name: Get All NACLs
  register: all_nacls
  ec2_vpc_nacl_facts:
    region: us-west-2

# Retrieve default Network ACLs:
- name: Get Default NACLs
  register: default_nacls
  ec2_vpc_nacl_facts:
    region: us-west-2
    filters:
      'default': 'true'
'''

RETURN = '''
nacl:
    description: Returns an array of complex objects as described below.
    returned: success
    type: complex
    contains:
        nacl_id:
            description: The ID of the Network Access Control List.
            returned: always
            type: string
        vpc_id:
            description: The ID of the VPC that the NACL is attached to.
            returned: always
            type: string
        is_default:
            description: True if the NACL is the default for its VPC.
            returned: always
            type: boolean
        tags:
            description: A dict of tags associated with the NACL.
            returned: always
            type: dict
        subnets:
            description: A list of subnet IDs that are associated with the NACL.
            returned: always
            type: list of string
        ingress:
            description: A list of NACL ingress rules.
            returned: always
            type: list of list
        egress:
            description: A list of NACL egress rules.
            returned: always
            type: list of list
'''

import traceback

try:
    from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
except ImportError:
    pass  # caught by imported HAS_BOTO3

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ec2 import (ec2_argument_spec, boto3_conn, get_aws_connection_info,
                                      ansible_dict_to_boto3_filter_list, HAS_BOTO3,
                                      camel_dict_to_snake_dict, boto3_tag_list_to_ansible_dict)


# VPC-supported IANA protocol numbers
# http://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml
PROTOCOL_NAMES = {'-1': 'all', '1': 'icmp', '6': 'tcp', '17': 'udp'}


def list_ec2_vpc_nacls(connection, module):

    nacl_ids = module.params.get("nacl_ids")
    filters = ansible_dict_to_boto3_filter_list(module.params.get("filters"))

    try:
        nacls = connection.describe_network_acls(NetworkAclIds=nacl_ids, Filters=filters)
    except (ClientError, NoCredentialsError) as e:
        module.fail_json(msg=e.message, **camel_dict_to_snake_dict(e.response))

    # Turn the boto3 result in to ansible_friendly_snaked_names
    snaked_nacls = []
    for nacl in nacls['NetworkAcls']:
        snaked_nacls.append(camel_dict_to_snake_dict(nacl))

    # Turn the boto3 result in to ansible friendly tag dictionary
    for nacl in snaked_nacls:
        if 'tags' in nacl:
            nacl['tags'] = boto3_tag_list_to_ansible_dict(nacl['tags'], 'key', 'value')
        if 'entries' in nacl:
            nacl['egress'] = [nacl_entry_to_list(entry) for entry in nacl['entries']
                              if entry['rule_number'] != 32767 and entry['egress']]
            nacl['ingress'] = [nacl_entry_to_list(entry) for entry in nacl['entries']
                               if entry['rule_number'] != 32767 and not entry['egress']]
            del nacl['entries']
        if 'associations' in nacl:
            nacl['subnets'] = [a['subnet_id'] for a in nacl['associations']]
            del nacl['associations']
        if 'network_acl_id' in nacl:
            nacl['nacl_id'] = nacl['network_acl_id']
            del nacl['network_acl_id']

    module.exit_json(nacls=snaked_nacls)


def nacl_entry_to_list(entry):

    elist = [entry['rule_number'],
             PROTOCOL_NAMES[entry['protocol']],
             entry['rule_action'],
             entry['cidr_block']
             ]
    if entry['protocol'] == '1':
        elist = elist + [-1, -1]
    else:
        elist = elist + [None, None, None, None]

    if 'icmp_type_code' in entry:
        elist[4] = entry['icmp_type_code']['type']
        elist[5] = entry['icmp_type_code']['code']

    if 'port_range' in entry:
        elist[6] = entry['port_range']['from']
        elist[7] = entry['port_range']['to']

    return elist


def main():

    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            nacl_ids=dict(default=[], type='list', aliases=['nacl_id']),
            filters=dict(default={}, type='dict')
        )
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           mutually_exclusive=[['nacl_ids', 'filters']])

    if not HAS_BOTO3:
        module.fail_json(msg='boto3 required for this module')

    region, ec2_url, aws_connect_params = get_aws_connection_info(module, boto3=True)

    if region:
        try:
            connection = boto3_conn(module, conn_type='client', resource='ec2',
                                    region=region, endpoint=ec2_url, **aws_connect_params)
        except (NoCredentialsError, ProfileNotFound) as e:
            module.fail_json(msg=e.message, exception=traceback.format_exc(), **camel_dict_to_snake_dict(e.response))
    else:
        module.fail_json(msg="region must be specified")

    list_ec2_vpc_nacls(connection, module)


if __name__ == '__main__':
    main()
