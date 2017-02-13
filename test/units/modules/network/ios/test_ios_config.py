#
# (c) 2016 Red Hat Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import patch, MagicMock
from ansible.errors import AnsibleModuleExit
from ansible.modules.network.ios import ios_config
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes


def set_module_args(args):
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)

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
    except:
        pass

    fixture_data[path] = data
    return data


class TestIosConfigModule(unittest.TestCase):

    def setUp(self):
        self.mock_get_config = patch('ansible.modules.network.ios.ios_config.get_config')
        self.get_config = self.mock_get_config.start()

        self.mock_load_config = patch('ansible.modules.network.ios.ios_config.load_config')
        self.load_config = self.mock_load_config.start()

        self.mock_run_commands = patch('ansible.modules.network.ios.ios_config.run_commands')
        self.run_commands = self.mock_run_commands.start()

    def tearDown(self):
        self.mock_get_config.stop()
        self.mock_load_config.stop()
        self.mock_run_commands.stop()

    def execute_module(self, failed=False, changed=False, commands=None,
            sort=True, defaults=False):

        config_file = 'ios_config_defaults.cfg' if defaults else 'ios_config_config.cfg'
        self.get_config.return_value = load_fixture(config_file)
        self.load_config.return_value = None

        with self.assertRaises(AnsibleModuleExit) as exc:
            ios_config.main()

        result = exc.exception.result

        if failed:
            self.assertTrue(result['failed'], result)
        else:
            self.assertEqual(result.get('changed'), changed, result)

        if commands:
            if sort:
                self.assertEqual(sorted(commands), sorted(result['updates']), result['updates'])
            else:
                self.assertEqual(commands, result['updates'], result['updates'])

        return result

    def test_ios_config_unchanged(self):
        src = load_fixture('ios_config_config.cfg')
        set_module_args(dict(src=src))
        self.execute_module()

    def test_ios_config_src(self):
        src = load_fixture('ios_config_src.cfg')
        set_module_args(dict(src=src))
        commands = ['hostname foo', 'interface GigabitEthernet0/0',
                    'no ip address']
        self.execute_module(changed=True, commands=commands)

    def test_ios_config_backup(self):
        set_module_args(dict(backup=True))
        result = self.execute_module()
        self.assertIn('__backup__', result)

    def test_ios_config_save(self):
        set_module_args(dict(save=True))
        self.execute_module(changed=True)
        self.assertEqual(self.run_commands.call_count, 1)
        self.assertEqual(self.get_config.call_count, 0)
        self.assertEqual(self.load_config.call_count, 0)
        args = self.run_commands.call_args[0][1]
        self.assertIn('copy running-config startup-config\r', args)

    def test_ios_config_lines_wo_parents(self):
        set_module_args(dict(lines=['hostname foo']))
        commands = ['hostname foo']
        self.execute_module(changed=True, commands=commands)

    def test_ios_config_lines_w_parents(self):
        set_module_args(dict(lines=['shutdown'], parents=['interface GigabitEthernet0/0']))
        commands = ['interface GigabitEthernet0/0', 'shutdown']
        self.execute_module(changed=True, commands=commands)

    def test_ios_config_defaults(self):
        set_module_args(dict(lines=['no shutdown'], parents=['interface GigabitEthernet0/0'],
                             defaults=True))
        self.execute_module(defaults=True)

    def test_ios_config_before(self):
        set_module_args(dict(lines=['hostname foo'], before=['test1','test2']))
        commands = ['test1', 'test2', 'hostname foo']
        self.execute_module(changed=True, commands=commands, sort=False)

    def test_ios_config_after(self):
        set_module_args(dict(lines=['hostname foo'], after=['test1','test2']))
        commands = ['hostname foo', 'test1', 'test2']
        self.execute_module(changed=True, commands=commands, sort=False)

    def test_ios_config_before_after_no_change(self):
        set_module_args(dict(lines=['hostname router'],
                             before=['test1', 'test2'],
                             after=['test3','test4']))
        self.execute_module()

    def test_ios_config_config(self):
        config = 'hostname localhost'
        set_module_args(dict(lines=['hostname router'], config=config))
        commands = ['hostname router']
        self.execute_module(changed=True, commands=commands)

    def test_ios_config_replace_block(self):
        lines = ['description test string', 'test string']
        parents = ['interface GigabitEthernet0/0']
        set_module_args(dict(lines=lines, replace='block', parents=parents))
        commands = parents + lines
        self.execute_module(changed=True, commands=commands)

    def test_ios_config_force(self):
        lines = ['hostname router']
        set_module_args(dict(lines=lines, force=True))
        self.execute_module(changed=True, commands=lines)

    def test_ios_config_match_none(self):
        lines = ['ip address 1.2.3.4 255.255.255.0', 'description test string']
        parents = ['interface GigabitEthernet0/0']
        set_module_args(dict(lines=lines, parents=parents, match='none'))
        commands = parents + lines
        self.execute_module(changed=True, commands=commands, sort=False)

    def test_ios_config_match_strict(self):
        lines = ['ip address 1.2.3.4 255.255.255.0', 'description test string',
                 'shutdown']
        parents = ['interface GigabitEthernet0/0']
        set_module_args(dict(lines=lines, parents=parents, match='strict'))
        commands = parents + ['shutdown']
        self.execute_module(changed=True, commands=commands, sort=False)

    def test_ios_config_match_exact(self):
        lines = ['ip address 1.2.3.4 255.255.255.0', 'description test string',
                 'shutdown']
        parents = ['interface GigabitEthernet0/0']
        set_module_args(dict(lines=lines, parents=parents, match='exact'))
        commands = parents + lines
        self.execute_module(changed=True, commands=commands, sort=False)
