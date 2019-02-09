#!/usr/bin/python
#
# Copyright (c) 2018 Zim Kalinowski, <zikalino@microsoft.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: azure_rm_cosmosdbaccount_facts
version_added: "2.8"
short_description: Get Azure Database Account facts.
description:
    - Get facts of Azure Database Account.

options:
    resource_group:
        description:
            - Name of an Azure resource group.
        required: True
    name:
        description:
            - Cosmos DB database account name.
    tags:
        description:
            - Limit results by providing a list of tags. Format tags as 'key' or 'key:value'.

extends_documentation_fragment:
    - azure

author:
    - "Zim Kalinowski (@zikalino)"

'''

EXAMPLES = '''
  - name: Get instance of Database Account
    azure_rm_cosmosdbaccount_facts:
      resource_group: testrg
      name: testaccount

  - name: List instances of Database Account
    azure_rm_cosmosdbaccousnt_facts:
      resource_group: testrg
'''

RETURN = '''
accounts:
    description: A list of dictionaries containing facts for Database Account.
    returned: always
    type: complex
    contains:
        id:
            description:
                - The unique resource identifier of the database account.
            returned: always
            type: str
            sample: /subscriptions/subid/resourceGroups/testrg/providers/Microsoft.DocumentDB/databaseAccounts/testaccount
        resource_group:
            description:
                - Name of an Azure resource group.
            returned: always
            type: str
            sample: testrg
        name:
            description:
                - The name of the database account.
            returned: always
            type: str
            sample: testaccount
        location:
            description:
                - The location of the resource group to which the resource belongs.
            returned: always
            type: str
            sample: westus
        kind:
            description:
                - Indicates the type of database account.
            returned: always
            type: str
            sample: global_document_db
        consistency_policy:
            description:
                - Consistency policy.
            returned: always
            type: complex
                default_consistency_level:
                max_interval_in_seconds:
                max_staleness_prefix:
        failover_policies:
            description:
                - Failover policies.
            returned: always
            type: complex
                name:
                failover_priority:
                id:
        read_locations:
            description:
                - Read locations
            returned: always
            type: complex
                name:
                failover_priority:
                id:
                document_endpoint:
                provisioning_state:
        write_locations:
            description:
                - Write locations
            returned: always
            type: complex
                name:
                failover_priority:
                id:
                document_endpoint:
                provisioning_state:
        database_account_offer_type:
            description:
                - Offer type.
            returned: always
            type: str
            sample: Standard
        ip_range_filter:
            description:
                -
            returned: always
            type: str
            sample: 10.10.10.10
        is_virtual_network_filter_enabled:
            description:
                -
            returned: always
            type: bool
            sample: true
        enable_automatic_failover:
            description:
                -
            returned: always
            type: bool
            sample: true
        enable_cassandra:
            description:
                -
            returned: always
            type: bool
            sample: true
        enable_table:
            description:
                -
            returned: always
            type: bool
            sample: true
        enable_gremlin:
            description:
                -
            returned: always
            type: bool
            sample: true
        virtual_network_rules:
        enable_multiple_write_locations:
        document_endpoint:
            description:
                - Document endpoint.
            returned: always
            type: str
            sample: Succeeded
        provisioning_state:
            description:
                - Provisioning state of Cosmos DB.
            returned: always
            type: str
            sample: Succeeded
        tags:
            description:
                -
            returned: always
            type: complex
            sample: {}
'''

from ansible.module_utils.azure_rm_common import AzureRMModuleBase
from ansible.module_utils.common.dict_transformations import _camel_to_snake

try:
    from msrestazure.azure_exceptions import CloudError
    from azure.mgmt.cosmosdb import CosmosDB
    from msrest.serialization import Model
except ImportError:
    # This is handled in azure_rm_common
    pass


class AzureRMDatabaseAccountFacts(AzureRMModuleBase):
    def __init__(self):
        # define user inputs into argument
        self.module_arg_spec = dict(
            resource_group=dict(
                type='str',
                required=True
            ),
            name=dict(
                type='str'
            ),
            tags=dict(
                type='list'
            )
        )
        # store the results of the module operation
        self.results = dict(
            changed=False
        )
        self.mgmt_client = None
        self.resource_group = None
        self.name = None
        self.tags = None
        super(AzureRMDatabaseAccountFacts, self).__init__(self.module_arg_spec, supports_tags=False)

    def exec_module(self, **kwargs):
        for key in self.module_arg_spec:
            setattr(self, key, kwargs[key])
        self.mgmt_client = self.get_mgmt_svc_client(CosmosDB,
                                                    base_url=self._cloud_environment.endpoints.resource_manager)

        if self.name is not None:
            self.results['accounts'] = self.get()
        else:
            self.results['accounts'] = self.list_by_resource_group()
        return self.results

    def get(self):
        response = None
        results = []
        try:
            response = self.mgmt_client.accounts.get(resource_group_name=self.resource_group,
                                                              account_name=self.name)
            self.log("Response : {0}".format(response))
        except CloudError as e:
            self.log('Could not get facts for Database Account.')

        if response and self.has_tags(response.tags, self.tags):
            results.append(self.format_response(response))

        return results

    def list_by_resource_group(self):
        response = None
        results = []
        try:
            response = self.mgmt_client.accounts.list_by_resource_group(resource_group_name=self.resource_group)
            self.log("Response : {0}".format(response))
        except CloudError as e:
            self.log('Could not get facts for Database Account.')

        if response is not None:
            for item in response:
                if self.has_tags(item.tags, self.tags):
                    results.append(self.format_response(item))

        return results

    def format_response(self, item):
        d = item.as_dict()
        d = {
            'id': d.get('id', None),
            'resource_group': self.resource_group,
            'name': d.get('name', None),
            'location': d.get('location', '').replace(' ', '').lower(),
            'kind': _camel_to_snake(d.get('kind', None)),
            'consistency_policy': {'default_consistency_level': _camel_to_snake(d['consistency_policy']['default_consistency_level']),
                                   'max_interval_in_seconds': d['consistency_policy']['max_interval_in_seconds'],
                                   'max_staleness_prefix': d['consistency_policy']['max_staleness_prefix']},
            'failover_policies': [{'name': fp['location_name'].replace(' ', '').lower(),
                                   'failover_priority': fp['failover_priority'],
                                   'id': fp['id']} for fp in d['failover_policies']],
            'read_locations': [{'name': rl['location_name'].replace(' ', '').lower(),
                                'failover_priority': rl['failover_priority'],
                                'id': rl['id'],
                                'document_endpoint': rl['document_endpoint'],
                                'provisioning_state': rl['provisioning_state']} for rl in d['read_locations']],
            'write_locations': [{'name': wl['location_name'].replace(' ', '').lower(),
                                 'failover_priority': wl['failover_priority'],
                                 'id': wl['id'],
                                 'document_endpoint': wl['document_endpoint'],
                                 'provisioning_state': wl['provisioning_state']} for wl in d['write_locations']],
            'database_account_offer_type': d.get('database_account_offer_type'),
            'ip_range_filter': d['ip_range_filter'],
            'is_virtual_network_filter_enabled': d.get('is_virtual_network_filter_enabled'),
            'enable_automatic_failover': d.get('enable_automatic_failover'),
            'enable_cassandra': 'EnableCassandra' in d.get('capabilities', []),
            'enable_table':  'EnableCassandra' in d.get('capabilities', []),
            'enable_gremlin': 'EnableGremlin' in d.get('capabilities', []),
            'virtual_network_rules': d.get('virtual_network_rules'),
            'enable_multiple_write_locations': d.get('enable_multiple_write_locations'),
            'document_endpoint': d.get('document_endpoint'),
            'provisioning_state': d.get('provisioning_state'),
            'tags': d.get('tags', None)
        }
        return d


def main():
    AzureRMDatabaseAccountFacts()


if __name__ == '__main__':
    main()
