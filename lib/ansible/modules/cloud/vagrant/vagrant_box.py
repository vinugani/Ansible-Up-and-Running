#!/usr/bin/python
# coding: utf-8 -*-

# Copyright (c), Chafik Belhaoues  <chafik.bel@gmail.com>, 2017
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: vagrant_box
short_description: Manage Vagrant boxes
version_added: "2.5"
author: "Chafik Belhaoues (@africanzoe)"
description:
   - This module can add|remove|update a Vagrant box on a target host.
options:
    box:
      description:
        - The name of the box to be managed, it could be a path to a file, URL or shorthand name from Vagrant cloud.
      aliases: ['path', 'url']
      required: true
    state:
      description:
        - Indicate the desired state of the box
      choices: ['present', 'absent', 'updated']
      default: present
    force:
      description:
        - Specify wether to force the add or remove actions.
      default: false
    version:
      description:
        - Specify the version of the managed box.
        - Please consider using an explicit version with the state "absent".
      default: latest
    provider:
      description:
        - Specify the provider for the box.
      choices: ['virtualbox', 'libvirt', 'hyperv', 'vmware_desktop']
      default: "virtualbox"
    insecure:
      description:
        - Indicate that the SSL certificates will not be verified if the URL is an HTTPS URL.
      default: false
    trust_location:
      description:
        - Indicate wether to trust 'Location' header from HTTP redirects and use the same credentials for subsequent urls as for the initial one or not.
      default: false
    cacert:
      description:
        - The path on the target host to the FILE that contains CA certificate for SSL download.
    capath:
      description:
        - The path on the target host to the DIRECTORY for the CA used to verify the peer.
      default: false
    cert:
      description:
        - The path on the target host to the a client certificate to use when downloading the box, if necessary.
    name:
      description:
        - The name to give to the box if added from a file.
        - When adding a box from a catalog, the name is included in the catalog entry and should not be specified.
      default: the basename of the file
    checksum:
      description:
        - The checksum for the box that is downloaded.
    checksum_type:
      description:
        - The hash algorithm used for the checksum.
      choices: ['md5', 'sha1', 'sha256']
      default: sha256
'''
EXAMPLES = '''
---
- name: Add Debian 9 box
  vagrant_box:
    box: "debian/stretch64"
    state: "present"
    provider: "virtualbox"
    version: "9.2.0"
    force: false

- name: Remove Ubuntu xenial64 box
  vagrant_box:
    box: "ubuntu/xenial64"
    state: "absent"
    provider: "virtualbox"
    version: "20170914.2.0"

- name: Update Centos 7 box
  vagrant_box:
    box: "centos/7"
    state: "updated"
    provider: "virtualbox"
'''

import os
import re

from ansible.module_utils.basic import AnsibleModule


class VagrantBox:
    def __init__(self, module):
        self.module = module
        self.changed = False
        self.box = module.params.get('box')
        self.state = module.params.get('state')
        self.force = module.params.get('force')
        self.version = module.params.get('version')
        self.provider = module.params.get('provider')
        self.insecure = module.params.get('insecure')
        self.trust_location = module.params.get('trust_location')
        self.cacert = module.params.get('cacert')
        self.capath = module.params.get('capath')
        self.cert = module.params.get('cert')
        self.name = module.params.get('name')
        self.checksum = module.params.get('checksum')
        self.checksum_type = module.params.get('checksum_type')

    def ispresent(self):
        cmd = "%s box list" % self.module.get_bin_path('vagrant', required=True)
        rc, out, err = self.module.run_command(cmd)
        if os.path.exists(self.box):
            if self.name:
                box = self.name
            else:
                box = os.path.basename(self.box)
        else:
            box = self.box
        if self.version is not "latest":
            result = re.search('%s[ \t]*\(%s, %s\)' % (box, self.provider, self.version), out)

            if result:
                return True
            else:
                return False

    def add(self):
        if self.ispresent() and not self.force:
            self.module.exit_json(changed=False, stdout="The box: '%s' version: '%s' provider: '%s' already exists" % (self.box, self.version, self.provider))

        opts_list = ['--clean']
        opts_dict = dict()
        # options only that DO NOT need a value
        if self.force:
            opts_list.append('--force')
        if self.insecure:
            opts_list.append('--insecure')
        if self.trust_location:
            opts_list.append('--location-trusted')

        # options that NEED a value
        opts_dict['--provider'] = self.provider
        if self.cacert:
            opts_dict['--cacert'] = self.cacert
        if self.capath:
            opts_dict['--capath'] = self.capath
        if self.cert:
            opts_dict['--cert'] = self.cert
        if self.version is not "latest":
            opts_dict['--box-version'] = self.version

        # conditional options, they are added ONLY IF the box is a filename
        if os.path.exists(self.box):
            if self.name:
                opts_dict['--name'] = self.name
            else:
                opts_dict['--name'] = os.path.basename(self.box)

            if self.checksum:
                opts_dict['--checksum'] = self.checksum
                opts_dict['--checksum-type'] = self.checksum_type

        if opts_dict:
            for k, v in opts_dict.items():
                opts_list.append(str(k) + " " + str(v))

        cmd = "%s box add %s %s" % (self.module.get_bin_path('vagrant', required=True), self.box, " ".join(opts_list))
        rc, out, err = self.module.run_command(cmd)

        if rc == 0:
            self.module.exit_json(changed=True, rc=rc, stdout=out, stderr=err)
        elif "already exists" in err:
            self.module.exit_json(changed=False, stdout="The box: '%s' version: '%s' provider: '%s' already exists" % (self.box, self.version, self.provider))
        else:
            self.module.fail_json(msg=err)

    def delete(self):
        if not self.ispresent() and self.version is not "latest":
            self.module.exit_json(changed=False, stdout="The box: '%s' version: '%s' provider: '%s' already removed" % (self.box, self.version, self.provider))

        opts_list = []
        if os.path.exists(self.box):
            if self.name:
                box = self.name
            else:
                box = os.path.basename(self.box)
        else:
            box = self.box
        if self.force:
            opts_list.append('--force')
        if self.provider:
            opts_list.append('--provider %s' % self.provider)
        if self.version is not "latest":
            opts_list.append('--box-version "%s"' % self.version)

        cmd = "%s box remove %s %s" % (self.module.get_bin_path('vagrant', required=True), box, " ".join(opts_list))
        rc, out, err = self.module.run_command(cmd)

        if rc == 0:
            self.module.exit_json(changed=True, rc=rc, stdout=out, stderr=err)
        elif "interface with the UI" in err:
            self.module.fail_json(msg="The box: '%s' is still in use by at least one Vagrant environment, use 'force' flag to force the deletion" % self.box)
        elif "could not be found" in err:
            self.module.exit_json(changed=False, stdout="The box: '%s' version: '%s' provider: '%s' already removed" % (box, self.version, self.provider))
        else:
            self.module.fail_json(msg=err, rc=rc)

    def update(self):
        if not self.ispresent() and self.version is not "latest":
            self.module.fail_json(msg="The box: '%s' version: '%s' provider: '%s' does not exist" % (self.box, self.version, self.provider))

        if os.path.exists(self.box):
            box = os.path.basename(self.box)
        else:
            box = self.box

        cmd = "%s box update --box %s --provider %s" % (self.module.get_bin_path('vagrant', required=True), box, self.provider)
        rc, out, err = self.module.run_command(cmd)

        if "is running the latest version" in out:
            self.module.exit_json(changed=False, rc=rc, stdout=out, stderr=err)
        elif rc == 0:
            self.module.exit_json(changed=True, rc=rc, stdout=out, stderr=err)
        else:
            self.module.fail_json(msg=err)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            box=dict(required=True, aliases=['path', 'url']),
            state=dict(choices=['present', 'absent', 'updated'], default="present"),
            force=dict(default=False, type='bool'),
            version=dict(default="latest"),
            provider=dict(choices=['hyperv', 'libvirt', 'virtualbox', 'vmware_desktop'], default="virtualbox"),
            insecure=dict(default=False, type='bool'),
            trust_location=dict(default=False, type='bool'),
            cacert=dict(type='path'),
            capath=dict(type='path'),
            cert=dict(type='path'),
            name=dict(),
            checksum=dict(),
            checksum_type=dict(choices=['md5', 'sha1', 'sha256'], default="sha256"),
        ),
        supports_check_mode=False,
    )
    module.run_command_environ_update = dict(LANG='C', LC_ALL='C', LC_MESSAGES='C', LC_CTYPE='C')

    vbox = VagrantBox(module)
    state = module.params.get('state')
    if state == "present":
        vbox.add()
    elif state == "absent":
        vbox.delete()
    else:
        vbox.update()

if __name__ == '__main__':
    main()
