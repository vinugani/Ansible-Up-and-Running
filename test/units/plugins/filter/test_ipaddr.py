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
from ansible.plugins.filter.ipaddr import ipaddr, _netmask_query


class TestNetmask(unittest.TestCase):
    def test_whole_octets(self):
        address = '1.1.1.1/24'
        self.assertEqual(ipaddr(address, 'netmask'), '255.255.255.0')

    def test_partial_octet(self):
        address = '1.1.1.1/25'
        self.assertEqual(ipaddr(address, 'netmask'), '255.255.255.128')

    def test_32_cidr(self):
        address = '1.12.1.34/32'
        self.assertEqual(ipaddr(address, 'netmask'), '255.255.255.255')

    def test_network_32(self):
        address = '1.12.1.34/32'
        self.assertEqual(ipaddr(address, 'network'), '1.12.1.34')

    def test_network_32_long(self):
        address = '1.12.1.34/255.255.255.255'
        self.assertEqual(ipaddr(address, 'network'), '1.12.1.34')

    def test_network_32_no_mask(self):
        address = '1.12.1.34'
        self.assertEqual(ipaddr(address, 'network'), '1.12.1.34')

    def test_network_31(self):
        address = '1.12.1.35/31'
        self.assertEqual(ipaddr(address, 'network'), '1.12.1.34')

    def test_network_24(self):
        address = '1.12.1.34/24'
        self.assertEqual(ipaddr(address, 'network'), '1.12.1.0')

    def test_broadcast_24(self):
        address = '1.12.1.34/24'
        self.assertEqual(ipaddr(address, 'broadcast'), '1.12.1.255')

    def test_broadcast_16(self):
        address = '1.12.1.34/16'
        self.assertEqual(ipaddr(address, 'broadcast'), '1.12.255.255')

    def test_broadcast_27(self):
        address = '1.12.1.34/27'
        self.assertEqual(ipaddr(address, 'broadcast'), '1.12.1.63')

    def test_broadcast_32(self):
        address = '1.12.1.34/32'
        self.assertEqual(ipaddr(address, 'broadcast'), None)

    def test_broadcast_31(self):
        address = '1.12.1.35/31'
        self.assertEqual(ipaddr(address, 'broadcast'), None)

