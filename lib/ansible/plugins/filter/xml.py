# (c) 2017, Christian Giese (@GIC-de)
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

from ansible.errors import AnsibleError

try:
    from lxml import etree
    parser = etree.XMLParser(remove_blank_text=True)
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


def xml_findtext(data, expr):
    if not HAS_LXML:
        raise AnsibleError('The lxml module is required but does not appear to be installed.')
    else:
        try:
            xml = etree.XML(data, parser=parser)
            result = xml.findtext(expr)
        except Exception as ex:
            raise AnsibleError('xml error: ' + str(ex))
        return result


class FilterModule(object):
    """XPATH Filter"""
    def filters(self):
        return {
            'xml_findtext': xml_findtext
        }
