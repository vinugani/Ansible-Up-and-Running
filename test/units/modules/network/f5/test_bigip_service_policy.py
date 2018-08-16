# -*- coding: utf-8 -*-
#
# Copyright: (c) 2017, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json
import pytest
import sys

from nose.plugins.skip import SkipTest
if sys.version_info < (2, 7):
    raise SkipTest("F5 Ansible modules require Python >= 2.7")

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import Mock
from ansible.compat.tests.mock import patch
from ansible.module_utils.basic import AnsibleModule

try:
    from test.unit import utils
except ImportError:
    pass

try:
    from library.modules.bigip_service_policy import ApiParameters
    from library.modules.bigip_service_policy import ModuleParameters
    from library.modules.bigip_service_policy import ModuleManager
    from library.modules.bigip_service_policy import ArgumentSpec
    from library.module_utils.network.f5.common import F5ModuleError
    from library.module_utils.network.f5.common import iControlUnexpectedHTTPError
    from test.unit.modules.utils import set_module_args
except ImportError:
    try:
        from ansible.modules.network.f5.bigip_service_policy import ApiParameters
        from ansible.modules.network.f5.bigip_service_policy import ModuleParameters
        from ansible.modules.network.f5.bigip_service_policy import ModuleManager
        from ansible.modules.network.f5.bigip_service_policy import ArgumentSpec
        from ansible.module_utils.network.f5.common import F5ModuleError
        from ansible.module_utils.network.f5.common import iControlUnexpectedHTTPError
        from units.modules.utils import set_module_args
    except ImportError:
        raise SkipTest("F5 Ansible modules require the f5-sdk Python library")

fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures')
fixture_data = {}


def load_fixture(name):
    path = os.path.join(fixture_path, name)

    if path in fixture_data:
        return fixture_data[path]

    with open(path) as f:
        data = f.read()

    try:
        data = json.loads(data)
    except Exception:
        pass

    fixture_data[path] = data
    return data


class TestParameters(unittest.TestCase):
    def test_module_parameters(self):
        args = dict(
            name='foo',
            description='my description',
            timer_policy='timer1',
            port_misuse_policy='misuse1',
        )

        p = ModuleParameters(params=args)
        assert p.name == 'foo'
        assert p.description == 'my description'
        assert p.timer_policy == '/Common/timer1'
        assert p.port_misuse_policy == '/Common/misuse1'

    def test_api_parameters(self):
        args = load_fixture('load_net_service_policy_1.json')
        p = ApiParameters(params=args)
        assert p.name == 'baz'
        assert p.description == 'my description'
        assert p.timer_policy == '/Common/foo'
        assert p.port_misuse_policy == '/Common/bar'


@patch('ansible.module_utils.f5_utils.AnsibleF5Client._get_mgmt_root',
       return_value=True)
class TestManager(unittest.TestCase):

    def setUp(self):
        self.spec = ArgumentSpec()

    def test_create_selfip(self, *args):
        set_module_args(dict(
            name='foo',
            description='my description',
            timer_policy='timer1',
            port_misuse_policy='misuse1',
            partition='Common',
            state='present',
            password='passsword',
            server='localhost',
            user='admin'
        ))

        module = AnsibleModule(
            argument_spec=self.spec.argument_spec,
            supports_check_mode=self.spec.supports_check_mode
        )
        mm = ModuleManager(module=module)

        # Override methods to force specific logic in the module to happen
        mm.exists = Mock(side_effect=[False, True])
        mm.create_on_device = Mock(return_value=True)
        mm.module_provisioned = Mock(return_value=True)

        results = mm.exec_module()

        assert results['changed'] is True
