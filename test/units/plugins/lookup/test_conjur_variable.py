# -*- coding: utf-8 -*-
# (c) 2018, Jason Vanderhoof <jason.vanderhoof@cyberark.com>
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


import pytest
from ansible.compat.tests.mock import MagicMock
from ansible.errors import AnsibleError
from ansible.module_utils.six.moves import http_client
from ansible.plugins.lookup import conjur_variable
import tempfile


class TestLookupModule:
    def test_valid_netrc_file(self):
        with tempfile.NamedTemporaryFile() as temp_netrc:
            temp_netrc.write(b"machine http://localhost/authn\n")
            temp_netrc.write(b"  login admin\n")
            temp_netrc.write(b"  password my-pass\n")
            temp_netrc.seek(0)

            results = conjur_variable._load_identity_from_file(temp_netrc.name, 'http://localhost')

            assert results['id'] == 'admin'
            assert results['api_key'] == 'my-pass'

    def test_netrc_without_host_file(self):
        with tempfile.NamedTemporaryFile() as temp_netrc:
            temp_netrc.write(b"machine http://localhost/authn\n")
            temp_netrc.write(b"  login admin\n")
            temp_netrc.write(b"  password my-pass\n")
            temp_netrc.seek(0)

            with pytest.raises(AnsibleError):
                conjur_variable._load_identity_from_file(temp_netrc.name, 'http://foo')

    def test_valid_configuration(self):
        with tempfile.NamedTemporaryFile() as configuration_file:
            configuration_file.write(b"---\n")
            configuration_file.write(b"account: demo-policy\n")
            configuration_file.write(b"plugins: []\n")
            configuration_file.write(b"appliance_url: http://localhost:8080\n")
            configuration_file.seek(0)

            results = conjur_variable._load_conf_from_file(configuration_file.name)
            assert results['account'] == 'demo-policy'
            assert results['appliance_url'] == 'http://localhost:8080'

    def mock_open_url_response(self, mocker, response_code, value):
        mock_response = MagicMock(spec_set=http_client.HTTPResponse)
        mock_response.read.return_value = value
        mock_response.getcode.return_value = response_code
        mocker.patch.object(conjur_variable, 'open_url', return_value=mock_response)

    def test_valid_token_retrieval(self, mocker):
        self.mock_open_url_response(mocker, 200, 'foo-bar-token')

        response = conjur_variable._fetch_conjur_token('http://conjur', 'account', 'username', 'api_key')
        assert response == 'foo-bar-token'

    def test_valid_fetch_conjur_variable(self, mocker):
        self.mock_open_url_response(mocker, 200, 'foo-bar')
        response = conjur_variable._fetch_conjur_token('super-secret', 'token', 'http://conjur', 'account')
        assert response == 'foo-bar'

    def test_invalid_fetch_conjur_variable(self, mocker):
        for code in [401, 403, 404]:
            self.mock_open_url_response(mocker, code, '')
            with pytest.raises(AnsibleError):
                response = conjur_variable._fetch_conjur_token('super-secret', 'token', 'http://conjur', 'account')
