#
#  Copyright 2018 Red Hat | Ansible
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

from __future__ import absolute_import, division, print_function


from ansible.module_utils.six import string_types
from ansible.module_utils.k8s.common import KubernetesAnsibleModule
from ansible.module_utils.common.dict_transformations import dict_merge


try:
    import yaml
    from openshift.dynamic.exceptions import DynamicApiError, NotFoundError, ConflictError, ForbiddenError
except ImportError:
    # Exceptions handled in common
    pass


class KubernetesRawModule(KubernetesAnsibleModule):

    def __init__(self, *args, **kwargs):
        self.client = None

        mutually_exclusive = [
            ('resource_definition', 'src'),
        ]

        KubernetesAnsibleModule.__init__(self, *args,
                                         mutually_exclusive=mutually_exclusive,
                                         supports_check_mode=True,
                                         **kwargs)

        kind = self.params.pop('kind')
        api_version = self.params.pop('api_version')
        name = self.params.pop('name')
        namespace = self.params.pop('namespace')
        resource_definition = self.params.pop('resource_definition')
        if resource_definition:
            if isinstance(resource_definition, string_types):
                try:
                    self.resource_definitions = yaml.safe_load_all(resource_definition)
                except (IOError, yaml.YAMLError) as exc:
                    self.fail(msg="Error loading resource_definition: {0}".format(exc))
            elif isinstance(resource_definition, list):
                self.resource_definitions = resource_definition
            else:
                self.resource_definitions = [resource_definition]
        src = self.params.pop('src')
        if src:
            self.resource_definitions = self.load_resource_definitions(src)

        if not resource_definition and not src:
            self.resource_definitions = [{
                'kind': kind,
                'apiVersion': api_version,
                'metadata': {
                    'name': name,
                    'namespace': namespace
                }
            }]

    def execute_module(self):
        changed = False
        results = []
        self.client = self.get_api_client()
        for definition in self.resource_definitions:
            kind = definition.get('kind')
            search_kind = kind
            if kind.lower().endswith('list'):
                search_kind = kind[:-4]
            api_version = definition.get('apiVersion')
            resource = self.find_resource(search_kind, api_version, fail=True)
            definition['kind'] = resource.kind
            definition['apiVersion'] = resource.group_version
            result = self.perform_action(resource, definition)
            changed = changed or result['changed']
            results.append(result)

        if len(results) == 1:
            self.exit_json(**results[0])

        self.exit_json(**{
            'changed': changed,
            'result': {
                'results': results
            }
        })

    def perform_action(self, resource, definition):
        result = {'changed': False, 'result': {}}
        state = self.params.get('state', None)
        force = self.params.get('force', False)
        name = definition.get('metadata', {}).get('name')
        namespace = definition.get('metadata', {}).get('namespace')
        existing = None

        self.remove_aliases()

        if definition['kind'].endswith('List'):
            result['result'] = resource.get(namespace=namespace).to_dict()
            result['changed'] = False
            result['method'] = 'get'
            return result

        try:
            existing = resource.get(name=name, namespace=namespace)
        except NotFoundError:
            pass
        except ForbiddenError as exc:
            if definition['kind'] in ['Project', 'ProjectRequest'] and state != 'absent':
                return self.create_project_request(definition)
            self.fail_json(msg='Failed to retrieve requested object: {0}'.format(exc.body),
                           error=exc.status, status=exc.status, reason=exc.reason)
        except DynamicApiError as exc:
            self.fail_json(msg='Failed to retrieve requested object: {0}'.format(exc.body),
                           error=exc.status, status=exc.status, reason=exc.reason)

        if state == 'absent':
            result['method'] = "delete"
            if not existing:
                # The object already does not exist
                return result
            else:
                # Delete the object
                if not self.check_mode:
                    try:
                        k8s_obj = resource.delete(name, namespace=namespace)
                        result['result'] = k8s_obj.to_dict()
                    except DynamicApiError as exc:
                        self.fail_json(msg="Failed to delete object: {0}".format(exc.body),
                                       error=exc.status, status=exc.status, reason=exc.reason)
                result['changed'] = True
                return result
        else:
            if not existing:
                if self.check_mode:
                    k8s_obj = definition
                else:
                    try:
                        k8s_obj = resource.create(definition, namespace=namespace).to_dict()
                    except ConflictError:
                        # Some resources, like ProjectRequests, can't be created multiple times,
                        # because the resources that they create don't match their kind
                        # In this case we'll mark it as unchanged and warn the user
                        self.warn("{0} was not found, but creating it returned a 409 Conflict error. This can happen \
                                  if the resource you are creating does not directly create a resource of the same kind.".format(name))
                        return result
                    except DynamicApiError as exc:
                        self.fail_json(msg="Failed to create object: {0}".format(exc.body),
                                       error=exc.status, status=exc.status, reason=exc.reason)
                result['result'] = k8s_obj
                result['changed'] = True
                result['method'] = 'create'
                return result

            match = False
            diffs = []

            if existing and force:
                if self.check_mode:
                    k8s_obj = definition
                else:
                    try:
                        k8s_obj = resource.replace(definition, name=name, namespace=namespace).to_dict()
                    except DynamicApiError as exc:
                        self.fail_json(msg="Failed to replace object: {0}".format(exc.body),
                                       error=exc.status, status=exc.status, reason=exc.reason)
                match, diffs = self.diff_objects(existing.to_dict(), k8s_obj)
                result['result'] = k8s_obj
                result['changed'] = not match
                result['method'] = 'replace'
                result['diff'] = diffs
                return result

            # Differences exist between the existing obj and requested params
            if self.check_mode:
                k8s_obj = dict_merge(existing.to_dict(), definition)
            else:
                try:
                    k8s_obj = resource.patch(definition, name=name, namespace=namespace).to_dict()
                except DynamicApiError as exc:
                    self.fail_json(msg="Failed to patch object: {0}".format(exc.body),
                                   error=exc.status, status=exc.status, reason=exc.reason)
            match, diffs = self.diff_objects(existing.to_dict(), k8s_obj)
            result['result'] = k8s_obj
            result['changed'] = not match
            result['method'] = 'patch'
            result['diff'] = diffs
            return result

    def create_project_request(self, definition):
        definition['kind'] = 'ProjectRequest'
        result = {'changed': False, 'result': {}}
        resource = self.find_resource('ProjectRequest', definition['apiVersion'], fail=True)
        if not self.check_mode:
            try:
                k8s_obj = resource.create(definition)
                result['result'] = k8s_obj.to_dict()
            except DynamicApiError as exc:
                self.fail_json(msg="Failed to create object: {0}".format(exc.body),
                               error=exc.status, status=exc.status, reason=exc.reason)
        result['changed'] = True
        result['method'] = 'create'
        return result
