# -*- coding: utf-8 -*-
# Copyright (c) 2019 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible.module_utils._text import to_native
from ansible.plugins.filter.core import fail, to_uuid
from ansible.errors import AnsibleFilterError


UUID_DEFAULT_NAMESPACE_TEST_CASES = (
    ('example.com', 'ae780c3a-a3ab-53c2-bfb4-098da300b3fe'),
    ('test.example', '8e437a35-c7c5-50ea-867c-5c254848dbc2'),
    ('café.example', '8a99d6b1-fb8f-5f78-af86-879768589f56'),
)

UUID_TEST_CASES = (
    ('361E6D51-FAEC-444A-9079-341386DA8E2E', 'example.com', 'ae780c3a-a3ab-53c2-bfb4-098da300b3fe'),
    ('361E6D51-FAEC-444A-9079-341386DA8E2E', 'test.example', '8e437a35-c7c5-50ea-867c-5c254848dbc2'),
    ('11111111-2222-3333-4444-555555555555', 'example.com', 'e776faa5-5299-55dc-9057-7a00e6be2364'),
)


@pytest.mark.parametrize('value, expected', UUID_DEFAULT_NAMESPACE_TEST_CASES)
def test_to_uuid_default_namespace(value, expected):
    assert expected == to_uuid(value)


@pytest.mark.parametrize('namespace, value, expected', UUID_TEST_CASES)
def test_to_uuid(namespace, value, expected):
    assert expected == to_uuid(value, namespace=namespace)


def test_to_uuid_invalid_namespace():
    with pytest.raises(AnsibleFilterError) as e:
        to_uuid('example.com', namespace='11111111-2222-3333-4444-555555555')
    assert 'Invalid value' in to_native(e.value)


def test_fail_throws_if_invoked():
    msg = "Expected failure"
    with pytest.raises(AnsibleFilterError) as e:
        fail(msg)
    assert msg in to_native(e.value)


def test_fail_falls_back_to_generic_message():
    msg = "Mandatory variable has not been overridden"
    with pytest.raises(AnsibleFilterError) as e:
        fail(None)
    assert msg in to_native(e.value)
