#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: aci_l3out
short_description: Manage Layer 3 Outside (L3Out) objects (l3ext:Out)
description:
- Manage Layer 3 Outside (L3Out) on Cisco ACI fabrics.
notes:
- The C(tenant) and C(domain) and C(vrf) used must exist before using this module in your playbook.
  The M(aci_tenant) and M(aci_domain) and M(aci_vrf) modules can be used for this.
- More information about the internal APIC class B(l3ext:Out) from
  L(the APIC Management Information Model reference,https://developer.cisco.com/docs/apic-mim-ref/).
author:
- Rostyslav Davydenko (@rost-d)
version_added: '2.5'
options:
  tenant:
    description:
    - Name of an existing tenant.
    required: yes
    aliases: [ tenant_name ]
  l3out:
    description:
    - Name of L3Out being created.
    required: yes
    aliases: [ l3out_name, name ]
  vrf:
    description:
    - Name of the VRF being associated with the L3Out.
    required: yes
    aliases: [ vrf_name ]
  domain:
    description:
    - Name of the external L3 domain being associated with the L3Out.
    required: yes
    aliases: [ ext_routed_domain_name, routed_domain ]
  target_dscp:
    description:
    - Target DSCP value.
    default: unspecified
  enforceRtctrl:
    description:
    - Route Control enforcement direction.
    choices: [ 'export,import', 'export' ]
    default: export
    aliases: [ route_control_enforcement ]
  l3protocol:
    description:
    - Route Control enforcement direction.
    choices: [ static, bgp, ospf ]
    default: static
  description:
    description:
    - Description for the L3Out.
    default:
    aliases: [ descr ]
  state:
    description:
    - Use C(present) or C(absent) for adding or removing.
    - Use C(query) for listing an object or multiple objects.
    choices: [ absent, present, query ]
    default: present
  method:
    description:
    - The HTTP method used for the request to the APIC
    choices: [ get, post, delete ]
    aliases: [ action ]
extends_documentation_fragment: aci
'''

EXAMPLES = r'''
- name: Add a new L3Out
  aci_epg:
    host: apic
    username: admin
    password: SomeSecretPassword
    tenant: production
    name: prod_l3out
    description: L3Out for Production tenant
    ext_routed_domain_name: l3dom_prod
    vrf: prod
    l3protocol: ospf,bgp

'''

RETURN = r'''
current:
  description: The existing configuration from the APIC after the module has finished
  returned: success
  type: list
  sample:
    [
        {
            "fvTenant": {
                "attributes": {
                    "descr": "Production environment",
                    "dn": "uni/tn-production",
                    "name": "production",
                    "nameAlias": "",
                    "ownerKey": "",
                    "ownerTag": ""
                }
            }
        }
    ]
error:
  description: The error information as returned from the APIC
  returned: failure
  type: dict
  sample:
    {
        "code": "122",
        "text": "unknown managed object class foo"
    }
raw:
  description: The raw output returned by the APIC REST API (xml or json)
  returned: parse error
  type: string
  sample: '<?xml version="1.0" encoding="UTF-8"?><imdata totalCount="1"><error code="122" text="unknown managed object class foo"/></imdata>'
sent:
  description: The actual/minimal configuration pushed to the APIC
  returned: info
  type: list
  sample:
    {
        "fvTenant": {
            "attributes": {
                "descr": "Production environment"
            }
        }
    }
previous:
  description: The original configuration from the APIC before the module has started
  returned: info
  type: list
  sample:
    [
        {
            "fvTenant": {
                "attributes": {
                    "descr": "Production",
                    "dn": "uni/tn-production",
                    "name": "production",
                    "nameAlias": "",
                    "ownerKey": "",
                    "ownerTag": ""
                }
            }
        }
    ]
proposed:
  description: The assembled configuration from the user-provided parameters
  returned: info
  type: dict
  sample:
    {
        "fvTenant": {
            "attributes": {
                "descr": "Production environment",
                "name": "production"
            }
        }
    }
filter_string:
  description: The filter string used for the request
  returned: failure or debug
  type: string
  sample: ?rsp-prop-include=config-only
method:
  description: The HTTP method used for the request to the APIC
  returned: failure or debug
  type: string
  sample: POST
response:
  description: The HTTP response from the APIC
  returned: failure or debug
  type: string
  sample: OK (30 bytes)
status:
  description: The HTTP status from the APIC
  returned: failure or debug
  type: int
  sample: 200
url:
  description: The HTTP url used for the request to the APIC
  returned: failure or debug
  type: string
  sample: https://10.11.12.13/api/mo/uni/tn-production.json
'''

from ansible.module_utils.network.aci.aci import ACIModule, aci_argument_spec
from ansible.module_utils.basic import AnsibleModule


def main():
    argument_spec = aci_argument_spec()
    argument_spec.update(
        l3out=dict(type='str', aliases=['l3out_name', 'name']),
        domain=dict(type='str', aliases=[
                    'ext_routed_domain_name', 'routed_domain']),
        vrf=dict(type='str', aliases=['vrf_name']),
        tenant=dict(type='str', aliases=['tenant_name']),
        description=dict(type='str', default='', aliases=['descr']),
        enforceRtctrl=dict(type='str', default='export', choices=[
                           'export,import', 'export'], aliases=['route_control_enforcement']),
        target_dscp=dict(type='str', default='unspecified'),
        l3protocol=dict(type='str', default='static',
                        choices=['static', 'bgp', 'ospf']),
        state=dict(type='str', default='present', choices=[
                   'absent', 'present', 'query']),
        method=dict(type='str', choices=['delete', 'get', 'post'], aliases=[
                    'action'], removed_in_version='2.6'),  # Deprecated starting from v2.6
        # Deprecated in v2.6
        protocol=dict(type='str', removed_in_version='2.6'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ['state', 'absent', ['name', 'tenant']],
            ['state', 'present', ['name', 'tenant', 'domain', 'vrf']],
        ],
    )

    aci = ACIModule(module)

    l3out = module.params['l3out']
    domain = module.params['domain']
    dscp = module.params['target_dscp']
    description = module.params['description']
    enforceRtctrl = module.params['enforceRtctrl']
    vrf = module.params['vrf']
    l3protocol = module.params['l3protocol']
    state = module.params['state']
    tenant = module.params['tenant']

    child_classes = ['l3extRsL3DomAtt', 'l3extRsEctx',
                     'bgpExtP', 'ospfExtP', 'eigrpExtP']

    aci.construct_url(
        root_class=dict(
            aci_class='fvTenant',
            aci_rn='tn-{0}'.format(tenant),
            filter_target='eq(fvTenant.name, "{0}")'.format(tenant),
            module_object=tenant,
        ),
        subclass_1=dict(
            aci_class='l3extOut',
            aci_rn='out-{0}'.format(l3out),
            filter_target='eq(l3extOut.name, "{0}")'.format(l3out),
            module_object=l3out,
        ),
        child_classes=child_classes,
    )

    aci.get_existing()

    child_configs = [
        dict(l3extRsL3DomAtt=dict(attributes=dict(
            tDn='uni/l3dom-{0}'.format(domain)))),
        dict(l3extRsEctx=dict(attributes=dict(tnFvCtxName=vrf))),
    ]
    if l3protocol == 'bgp':
        child_configs.append(
            dict(bgpExtP=dict(attributes=dict(descr='', nameAlias=''))))
    if l3protocol == 'ospf':
        child_configs.append(
            dict(ospfExtP=dict(attributes=dict(descr='', nameAlias=''))))

    if state == 'present':
        aci.payload(
            aci_class='l3extOut',
            class_config=dict(
                name=l3out,
                descr=description,
                dn='uni/tn-{0}/out-{1}'.format(tenant, l3out),
                enforceRtctrl=enforceRtctrl,
                targetDscp=dscp,
                nameAlias='',
                ownerKey='',
                ownerTag='',
            ),
            child_configs=child_configs,
        )

        aci.get_diff(aci_class='l3extOut')

        aci.post_config()

    elif state == 'absent':
        aci.delete_config()

    aci.exit_json()


if __name__ == "__main__":
    main()
