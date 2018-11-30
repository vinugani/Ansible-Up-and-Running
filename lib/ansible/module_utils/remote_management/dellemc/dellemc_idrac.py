# -*- coding: utf-8 -*-

#
# Dell EMC OpenManage Ansible Modules
# Version 1.0
# Copyright (C) 2018 Dell Inc.

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# All rights reserved. Dell, EMC, and other trademarks are trademarks of Dell Inc. or its subsidiaries.
# Other trademarks may be trademarks of their respective owners.
#

from __future__ import (absolute_import, division,
                        print_function)
import tempfile
import os
__metaclass__ = type

try:
    from omsdk.sdkinfra import sdkinfra
    from omsdk.sdkcreds import UserCredentials
    from omsdk.sdkfile import FileOnShare, file_share_manager
    from omsdk.sdkprotopref import ProtoPreference, ProtocolEnum
    from omsdk.http.sdkwsmanbase import WsManOptions
    HAS_OMSDK = True

except ImportError:

    HAS_OMSDK = False


class iDRACConnection:
    def __init__(self, module):
        if not HAS_OMSDK:
            results = {}
            results['msg'] = "Dell EMC OMSDK library is required for this module"
            module.fail_json(**results)

        self.module = module
        self.handle = None

    def connect(self):
        results = {}
        idrac = None

        ansible_module_params = self.module.params
        idrac_ip = ansible_module_params['idrac_ip']
        idrac_user = ansible_module_params['idrac_user']
        idrac_pwd = ansible_module_params['idrac_pwd']
        idrac_port = ansible_module_params['idrac_port']

        try:
            sd = sdkinfra()
            sd.importPath()
        except Exception as e:
            results['msg'] = "Could not initialize drivers"
            results['exception'] = str(e)
            self.module.fail_json(**results)

        # Connect to iDRAC
        if not all((idrac_ip, idrac_user, idrac_pwd)):
            results['msg'] = "hostname, username and password required"
            self.module.fail_json(**results)
        else:
            creds = UserCredentials(idrac_user, idrac_pwd)
            pOp = WsManOptions(port=idrac_port)

            idrac = sd.get_driver(sd.driver_enum.iDRAC, idrac_ip, creds, pOptions=pOp)

            if idrac is None:
                results['msg'] = "Could not find device driver for iDRAC with IP Address: " + idrac_ip
                self.module.fail_json(**results)

        self.handle = idrac
        return idrac

    def disconnect(self):
        if self.handle:
            self.handle.disconnect()
            return True

        return True
