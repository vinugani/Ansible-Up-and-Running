import json
import pytest

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import patch
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible.modules.remote_management.lxca import lxca_fanmuxes

import pylxca
import mock


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""
    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""
    pass


def exit_json(*args, **kwargs):
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)

def fake_conn(*arg, **kwargs):
    return "Fake connection"

class TestMyModule(unittest.TestCase):

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json,
                                                )
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)


    def test__required_args_missing(self):
        with self.assertRaises(AnsibleFailJson):
            set_module_args({
                "auth_url": "https://10.240.14.195",
                "login_user": "USERID",
            })
            lxca_fanmuxes.main()


    @mock.patch("ansible.modules.remote_management.lxca.lxca_fanmuxes.setup_conn", autospec=True)
    @mock.patch("ansible.modules.remote_management.lxca.lxca_fanmuxes.execute_module", autospec=True)
    @mock.patch("ansible.modules.remote_management.lxca.lxca_fanmuxes.AnsibleModule", autospec=True)
    def test__argument_spec(self, ansible_mod_cls, _execute_module, _setup_conn):
        expected_arguments_spec = dict(
            login_user=dict(required=True),
            login_password=dict(required=True, no_log=True),
            command_options=dict(default='fanmuxes', choices=['fanmuxes', 'fanmuxes_by_uuid',
                                                              'fanmuxes_by_chassis_uuid']),
            auth_url=dict(required=True),
            uuid=dict(default=None),
            chassis=dict(default=None),
            noverify=dict(default=True),
        )
        _setup_conn.return_value = "Fake connection"
        _execute_module.return_value = []
        mod_obj = ansible_mod_cls.return_value
        args = {
            "auth_url": "https://10.243.30.195",
            "login_user": "USERID",
            "login_password": "CME44ibm",
            "command_options": "fanmuxes",
        }
        mod_obj.params = args
        lxca_fanmuxes.main()
        assert mock.call(argument_spec=expected_arguments_spec,
                         supports_check_mode=False) == ansible_mod_cls.call_args

    @mock.patch("ansible.modules.remote_management.lxca.lxca_fanmuxes._fanmuxes_by_uuid",
                autospec=True)
    @mock.patch("ansible.modules.remote_management.lxca.pylxca_module.AnsibleModule",
                autospec=True)
    def test__fanmuxes_empty_list(self, ansible_mod_cls, _get_fanmuxes):
        mod_obj = ansible_mod_cls.return_value
        args = {
            "auth_url": "https://10.243.30.195",
            "login_user": "USERID",
            "login_password": "CME44ibm",
            "uuid": "3C737AA5E31640CE949B10C129A8B01F",
            "command_options": "fanmuxes_by_uuid",
        }
        mod_obj.params = args
        _get_fanmuxes.return_value = []
        ret_fanmuxes = _get_fanmuxes(mod_obj, args)
        assert mock.call(mod_obj, mod_obj.params) == _get_fanmuxes.call_args
        assert _get_fanmuxes.return_value == ret_fanmuxes

    '''
    @mock.patch("ansible.modules.remote_management.lxca.lxca_fanmuxes._fanmuxes", autospec=True)
    @mock.patch("ansible.modules.remote_management.lxca.pylxca_module.AnsibleModule", autospec=True)
    def test__nodes_throw_exception(self, ansible_mod_cls, _get_fanmuxes):
        mod_obj = ansible_mod_cls.return_value
        args = {
            "auth_url": "https://10.243.30.195",
            "login_user": "USERID",
            "login_password": "CME44ibm",
            "command_options": "fanmuxes",
        }
        mod_obj.params = args
        _get_fanmuxes.side_effect = "failed to get fanmuxes"
        with self.assertRaises(AnsibleFailJson):
            lxca_fanmuxes.main()

    '''