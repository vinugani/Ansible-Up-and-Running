# Copyright 2012, Jeroen Hoekx <jeroen@hoekx.be>
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

import ansible

from ansible.runner.return_data import ReturnData

class ActionModule(object):
    ''' Create inventory groups based on variables '''

    ### We need to be able to modify the inventory
    BYPASS_HOST_LOOP = True

    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject):
        variables = module_args.strip().split(',')
        inventory = self.runner.inventory

        result = {'changed': False}

        for variable in variables:
            if not variable:
                continue ### ignore trailing comma
            variable = variable.strip()

            ### find all returned groups
            groups = {}
            for _,host in self.runner.host_set:
                data = self.runner.setup_cache[host]
                if variable in data:
                    if data[variable] not in groups:
                        groups[data[variable]] = []
                    groups[data[variable]].append(host)

            result[variable] = groups

            ### add to inventory
            for group, hosts in groups.items():
                inv_group = inventory.get_group(group)
                if not inv_group:
                    inv_group = ansible.inventory.Group(name=group)
                    inventory.add_group(inv_group)
                for host in hosts:
                    inv_host = inventory.get_host(host)
                    if not inv_host:
                        inv_host = ansible.inventory.Host(name=host)
                    if inv_group not in inv_host.get_groups():
                        result['changed'] = True
                        inv_group.add_host(inv_host)

        return ReturnData(conn=conn, comm_ok=True, result=result)
