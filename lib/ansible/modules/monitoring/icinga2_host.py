#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: icinga2_host
short_description: Manage a host in Icinga2
description:
   - "Add or remove a host to Icinga2 through the API"
   - "( see https://www.icinga.com/docs/icinga2/latest/doc/12-icinga2-api/ )"
version_added: "2.5"
author: "Jurgen Brand"
options:
  url:
    description:
      - HTTP, HTTPS, or FTP URL in the form (http|https|ftp)://[user[:pass]]@host.domain[:port]/path
    required: true
  force:
    description:
      - If C(yes) and C(dest) is not a directory, will download the file every
        time and replace the file if the contents change. If C(no), the file
        will only be downloaded if the destination does not exist. Generally
        should be C(yes) only for small local files.
      - Prior to 0.6, this module behaved as if C(yes) was the default.
    version_added: '0.7'
    default: 'no'
    type: bool
    aliases: [ thirsty ]
  use_proxy:
    description:
      - if C(no), it will not use a proxy, even if one is defined in
        an environment variable on the target hosts.
    default: 'yes'
    type: bool
  validate_certs:
    description:
      - If C(no), SSL certificates will not be validated. This should only be used
        on personally controlled sites using self-signed certificates.
    default: 'yes'
    type: bool
  url_username:
    description:
      - The username for use in HTTP basic authentication.
      - This parameter can be used without C(url_password) for sites that allow empty passwords.
    version_added: '1.6'
  url_password:
    description:
        - The password for use in HTTP basic authentication.
        - If the C(url_username) parameter is not specified, the C(url_password) parameter will not be used.
    version_added: '1.6'
  force_basic_auth:
    version_added: '2.0'
    description:
      - httplib2, the library used by the uri module only sends authentication information when a webservice
        responds to an initial request with a 401 status. Since some basic auth services do not properly
        send a 401, logins will fail. This option forces the sending of the Basic authentication header
        upon initial request.
    default: 'no'
    type: bool
  client_cert:
    description:
      - PEM formatted certificate chain file to be used for SSL client
        authentication. This file can also include the key as well, and if
        the key is included, C(client_key) is not required.
    version_added: '2.4'
  client_key:
    description:
      - PEM formatted file that contains your private key to be used for SSL
        client authentication. If C(client_cert) contains both the certificate
        and key, this option is not required.
    version_added: '2.4'
  state:
    description:
      - Apply feature state.
    required: false
    choices: [ "present", "absent" ]
    default: present
  name:
    description:
      - name used to create / delete the host
      - this does not need to be the FQDN, but does needs to be uniuqe
    required: true
    default: null
  zone:
    description:
      - ??
    required: false
    default: None
  template:
    description:
      - the template used to define the host
    required: false
    default: None
  check_command:
    description:
      - the command used to check if the host is alive
    required: false
    default: "hostalive"
  display_name:
    description:
      - the name used to display the host
    required: false
    default: <name>
  ip:
    description:
      - the ip-addres of the host
    required: true
  variables:
    description:
      - list of variables
    required: false
    default: None
'''

EXAMPLES = '''
- name: Add host to icinga
  icinga_host:
    icinga_server: "icinga.example.com"
    icinga_user: "anisble"
    icinga_pass: "mypassword"
    state: present
    name: "{{ansible_fqdn }}"
    ip_address: "{{ ansible_default_ipv4.address }}"
'''

RETURN = '''
#
'''

import json
import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url, url_argument_spec


# ===========================================
# Icinga2 API class
#
class icinga2_api:
    module = None

    def call_url(self, path, data='', method='GET'):
        headers = {
            'Accept': 'application/json',
            'X-HTTP-Method-Override': method,
        }
        url = self.module.params.get("url") + "/" + path
        rsp, info = fetch_url(module=self.module, url=url, data=data, headers=headers, method=method)
        body = ''
        if rsp:
            body = json.loads(rsp.read())
        if info['status'] >= 400:
            body = info['body']
        return {'code': info['status'], 'data': body}

    def check_connection(self):
        ret = self.call_url('v1/status')
        if ret['code'] == 200:
            return True
        return False

    def exists(self, hostname):
        data = {
            "filter": "match(\"" + hostname + "\", host.name)",
        }
        ret = self.call_url(
            path="v1/objects/hosts",
            data=self.module.jsonify(data)
        )
        if ret['code'] == 200:
            if len(ret['data']['results']) == 1:
                return True
        return False

    def create(self, hostname, data):
        ret = self.call_url(
            path="v1/objects/hosts/" + hostname,
            data=self.module.jsonify(data),
            method="PUT"
        )
        return ret

    def delete(self, hostname):
        data = {"cascade": 1}
        ret = self.call_url(
            path="v1/objects/hosts/" + hostname,
            data=self.module.jsonify(data),
            method="DELETE"
        )
        return ret

    def modify(self, hostname, data):
        ret = self.call_url(
            path="v1/objects/hosts/" + hostname,
            data=self.module.jsonify(data),
            method="POST"
        )
        return ret

    def diff(self, hostname, data):
        ret = self.call_url(
            path="v1/objects/hosts/" + hostname,
            method="GET"
        )
        changed = False
        ic_data = ret['data']['results'][0]
        for key in data['attrs']:
            if key not in ic_data['attrs'].keys():
                changed = True
            elif data['attrs'][key] != ic_data['attrs'][key]:
                changed = True
        return changed


# ===========================================
# Module execution.
#
def main():
    # use the predefined argument spec for url
    argument_spec = url_argument_spec()
    # add our own arguments
    argument_spec.update(
        state=dict(default="present", choices=["absent", "present"]),
        name=dict(required=True, aliases=['host']),
        zone=dict(default=None),
        template=dict(default=None),
        check_command=dict(default="hostalive"),
        display_name=dict(default=None),
        ip=dict(required=True),
        variables=dict(type='dict', default=None),
    )

    # Define the main module
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    state = module.params["state"]
    name = module.params["name"]
    zone = module.params["zone"]
    template = []
    template.append(name)
    if module.params["template"]:
        template.append(module.params["template"])
    check_command = module.params["check_command"]
    ip = module.params["ip"]
    display_name = module.params["display_name"]
    if not display_name:
        display_name = name
    variables = module.params["variables"]

    try:
        icinga = icinga2_api()
        icinga.module = module
        icinga.check_connection()
    except Exception as e:
        module.fail_json(msg="unable to connect to Icinga. Exception message: %s" % (e))

    data = {
        'attrs': {
            'address': ip,
            'display_name': display_name,
            'check_command': check_command,
            'zone': zone,
            'vars': {
                'made_by': "ansible",
            },
            'templates': template,
        }
    }

    if variables:
        data['attrs']['vars'].update(variables)

    changed = False
    if icinga.exists(name):
        if state == "absent":
            if module.check_mode:
                module.exit_json(changed=True, name=name, data=data)
            else:
                try:
                    ret = icinga.delete(name)
                    if ret['code'] == 200:
                        changed = True
                    else:
                        module.fail_json(msg="bad return code deleting host: %s" % (ret['data']))
                except Exception as e:
                    module.fail_json(msg="exception deleting host: " + str(e))
                module.exit_json(changed=changed, name=name, data=data)

        elif icinga.diff(name, data):
            if module.check_mode:
                module.exit_json(changed=False, name=name, data=data)
            ret = icinga.modify(name, data)
            if ret['code'] == 200:
                changed = True
            else:
                module.fail_json(msg="bad return code modifying host: %s" % (ret['data']))

        module.exit_json(changed=changed, name=name, data=data)

    else:
        if state == "present":
            if module.check_mode:
                changed = True
            else:
                try:
                    ret = icinga.create(name, data)
                    if ret['code'] == 200:
                        changed = True
                    else:
                        module.fail_json(msg="bad return code creating host: %s" % (ret['data']))
                except Exception as e:
                    module.fail_json(msg="exception creating host: " + str(e))
        elif icinga.diff(name, data):
            if module.check_mode:
                module.exit_json(changed=False, name=name, data=data)
            ret = icinga.modify(name, data)
            if ret['code'] == 200:
                changed = True
            else:
                module.fail_json(msg="bad return code modifying host: %s" % (ret['data']))

        module.exit_json(changed=changed, name=name, data=data)


# import module snippets
if __name__ == '__main__':
    main()
