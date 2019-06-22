#
# Copyright (c) 2019 Ericsson AB.
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.common._collections_compat import Mapping
import collections
import re
import time
import json

from itertools import chain

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils._text import to_text
from ansible.module_utils.six import iteritems
from ansible.module_utils.network.common.config import NetworkConfig, dumps
from ansible.module_utils.network.common.utils import to_list
from ansible.plugins.cliconf import CliconfBase, enable_mode


class Cliconf(CliconfBase):

    def get_config(self, source='running', flags=None, format=None):
        return

    def edit_config(self, candidate=None, commit=True, replace=None, comment=None):
        return

    def get(self, command=None, prompt=None, answer=None, sendonly=False, output=None, check_all=False):
        if not command:
            raise ValueError('must provide value of command to execute')
        if output:
            raise ValueError("'output' value %s is not supported for get" % output)

        return self.send_command(command=command, prompt=prompt, answer=answer, sendonly=sendonly, check_all=check_all)

    def get_device_info(self):
        device_info = {}
        device_info['network_os'] = 'eric_eccli'
        return device_info

    def get_capabilities(self):
        result = dict()
        result['rpc'] = self.get_base_rpc() + ['run_commands']
        result['network_api'] = 'cliconf'
        result['device_info'] = self.get_device_info()
        return json.dumps(result)

    def run_commands(self, commands=None, check_rc=True):
        if commands is None:
            raise ValueError("'commands' value is required")

        responses = list()
        for cmd in to_list(commands):
            if not isinstance(cmd, Mapping):
                cmd = {'command': cmd}

            output = cmd.pop('output', None)
            if output:
                raise ValueError("'output' value %s is not supported for run_commands" % output)
            try:
                out = self.send_command(**cmd)
            except AnsibleConnectionFailure as e:
                if check_rc:
                    raise
                out = getattr(e, 'err', e)

            responses.append(out)

        return responses
