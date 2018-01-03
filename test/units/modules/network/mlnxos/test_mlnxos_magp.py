#
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.compat.tests.mock import patch
from ansible.modules.network.mlnxos import mlnxos_magp
from units.modules.utils import set_module_args
from .mlnxos_module import TestMlnxosModule, load_fixture


class TestMlnxosMagpModule(TestMlnxosModule):

    module = mlnxos_magp

    def setUp(self):
        super(TestMlnxosMagpModule, self).setUp()
        self.mock_get_config = patch.object(
            mlnxos_magp.MlnxosMagpModule,
            "_get_magp_config")
        self.get_config = self.mock_get_config.start()

        self.mock_load_config = patch(
            'ansible.module_utils.network.mlnxos.mlnxos.load_config')
        self.load_config = self.mock_load_config.start()

    def tearDown(self):
        super(TestMlnxosMagpModule, self).tearDown()
        self.mock_get_config.stop()
        self.mock_load_config.stop()

    def load_fixtures(self, commands=None, transport='cli'):
        config_file = 'mlnxos_magp_show.cfg'
        self.get_config.return_value = load_fixture(config_file)
        self.load_config.return_value = None

    def test_magp_absent_no_change(self):
        set_module_args(dict(interface='Vlan 1002', magp_id=110,
                             state='absent'))
        self.execute_module(changed=False)

    def test_magp_no_change(self):
        set_module_args(dict(interface='Vlan 1200', magp_id=103,
                             state='disabled'))
        self.execute_module(changed=False)

    def test_magp_present_no_change(self):
        set_module_args(dict(interface='Vlan 1200', magp_id=103))
        self.execute_module(changed=False)

    def test_magp_enable(self):
        set_module_args(dict(interface='Vlan 1200', magp_id=103,
                             state='enabled'))
        commands = ['interface vlan 1200 magp 103 no shutdown']
        self.execute_module(changed=True, commands=commands)

    def test_magp_disable(self):
        set_module_args(dict(interface='Vlan 1243', magp_id=102,
                             state='disabled', router_ip='10.0.0.43',
                             router_mac='01:02:03:04:05:06'))
        commands = ['interface vlan 1243 magp 102 shutdown']
        self.execute_module(changed=True, commands=commands)

    def test_magp_change_address(self):
        set_module_args(dict(interface='Vlan 1243', magp_id=102,
                             router_ip='10.0.0.44',
                             router_mac='01:02:03:04:05:07'))
        commands = [
            'interface vlan 1243 magp 102 ip virtual-router address 10.0.0.44',
            'interface vlan 1243 magp 102 ip virtual-router mac-address 01:02:03:04:05:07']
        self.execute_module(changed=True, commands=commands)

    def test_magp_remove_address(self):
        set_module_args(dict(interface='Vlan 1243', magp_id=102))
        commands = [
            'interface vlan 1243 magp 102 no ip virtual-router address',
            'interface vlan 1243 magp 102 no ip virtual-router mac-address']
        self.execute_module(changed=True, commands=commands)

    def test_magp_add(self):
        set_module_args(dict(interface='Vlan 1244', magp_id=104,
                             router_ip='10.0.0.44',
                             router_mac='01:02:03:04:05:07'))
        commands = [
            'interface vlan 1244 magp 104',
            'exit',
            'interface vlan 1244 magp 104 ip virtual-router address 10.0.0.44',
            'interface vlan 1244 magp 104 ip virtual-router mac-address 01:02:03:04:05:07']
        self.execute_module(changed=True, commands=commands, sort=False)

    def test_magp_change_vlan(self):
        set_module_args(dict(interface='Vlan 1244', magp_id=102,
                             router_ip='10.0.0.43',
                             router_mac='01:02:03:04:05:06'))
        commands = [
            'interface vlan 1243 no magp 102',
            'interface vlan 1244 magp 102',
            'exit',
            'interface vlan 1244 magp 102 ip virtual-router address 10.0.0.43',
            'interface vlan 1244 magp 102 ip virtual-router mac-address 01:02:03:04:05:06']
        self.execute_module(changed=True, commands=commands)
