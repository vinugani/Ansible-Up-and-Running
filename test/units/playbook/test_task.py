# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
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

from ansible.compat.tests import unittest
from ansible.playbook.task import Task

from units.mock.compare_helpers import TotalOrdering, EqualityCompare, IdentityCompare, HashCompare, DifferentType
from units.mock.compare_helpers import UuidCompare, CopyCompare, CopyExcludeParentCompare
from units.mock.compare_helpers import CopyExcludeTasksCompare
from units.mock.loader import DictDataLoader


basic_command_task = dict(
    name='Test Task',
    command='echo hi'
)

kv_command_task = dict(
    action='command echo hi'
)


class TestTaskCompare(unittest.TestCase, EqualityCompare, TotalOrdering,
                      IdentityCompare, HashCompare, UuidCompare,
                      CopyCompare, CopyExcludeParentCompare, CopyExcludeTasksCompare):

    def setUp(self):
        fake_loader = DictDataLoader({})

        one_ds = {'name': 'base_one',
                  'command': 'echo base_one'}

        self.one = Task.load(one_ds, loader=fake_loader)

        two_ds = {'name': 'base_two',
                  'command': 'echo base_two'}

        self.two = Task.load(two_ds, loader=fake_loader)

        self.another_one = self.one.copy()
        self.one_copy = self.one.copy()
        self.one_copy_exclude_parent = self.one.copy(exclude_parent=True)
        self.one_copy_exclude_tasks = self.one.copy(exclude_tasks=True)

        self.different = DifferentType()


class TestTask(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_construct_empty_task(self):
        t = Task()

    def test_construct_task_with_role(self):
        pass

    def test_construct_task_with_block(self):
        pass

    def test_construct_task_with_role_and_block(self):
        pass

    def test_load_task_simple(self):
        t = Task.load(basic_command_task)
        assert t is not None
        self.assertEqual(t.name, basic_command_task['name'])
        self.assertEqual(t.action, 'command')
        self.assertEqual(t.args, dict(_raw_params='echo hi'))

    def test_load_task_kv_form(self):
        t = Task.load(kv_command_task)
        self.assertEqual(t.action, 'command')
        self.assertEqual(t.args, dict(_raw_params='echo hi'))

    def test_task_auto_name(self):
        assert 'name' not in kv_command_task
        t = Task.load(kv_command_task)
        # self.assertEqual(t.name, 'shell echo hi')

    def test_task_auto_name_with_role(self):
        pass

    def test_load_task_complex_form(self):
        pass

    def test_can_load_module_complex_form(self):
        pass

    def test_local_action_implies_delegate(self):
        pass

    def test_local_action_conflicts_with_delegate(self):
        pass

    def test_delegate_to_parses(self):
        pass
