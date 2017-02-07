
# -*- coding: utf-8 -*-
from ansible.compat.tests import mock
from ansible.compat.tests import unittest

from ansible.modules.packaging.os import yum


yum_plugin_load_error = """
Plugin "product-id" can't be imported
Plugin "search-disabled-repos" can't be imported
Plugin "subscription-manager" can't be imported
Plugin "product-id" can't be imported
Plugin "search-disabled-repos" can't be imported
Plugin "subscription-manager" can't be imported
"""

# from https://github.com/ansible/ansible/issues/20608#issuecomment-276106505
wrapped_output_1 = """
Загружены модули: fastestmirror
Loading mirror speeds from cached hostfile
 * base: mirror.h1host.ru
 * extras: mirror.h1host.ru
 * updates: mirror.h1host.ru

vms-agent.x86_64                            0.0-9                            dev
"""

# from https://github.com/ansible/ansible/issues/20608#issuecomment-276971275
wrapped_output_2 = """
Загружены модули: fastestmirror
Loading mirror speeds from cached hostfile
 * base: mirror.corbina.net
 * extras: mirror.corbina.net
 * updates: mirror.corbina.net

empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty.x86_64
                                    0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.1-0
                                                                         addons
libtiff.x86_64                      4.0.3-27.el7_3                       updates
"""

yum_check_update_output_rhel7 = """

Loaded plugins: etckeeper, product-id, search-disabled-repos, subscription-
              : manager
This system is not registered to Red Hat Subscription Management. You can use subscription-manager to register.

NetworkManager-openvpn.x86_64         1:1.2.6-1.el7           epel
NetworkManager-openvpn-gnome.x86_64   1:1.2.6-1.el7           epel
cabal-install.x86_64                  1.16.1.0-2.el7          epel
cgit.x86_64                           1.1-1.el7               epel
python34-libs.x86_64                  3.4.5-3.el7             epel
python34-test.x86_64                  3.4.5-3.el7             epel
python34-tkinter.x86_64               3.4.5-3.el7             epel
python34-tools.x86_64                 3.4.5-3.el7             epel
qgit.x86_64                           2.6-4.el7               epel
rdiff-backup.x86_64                   1.2.8-12.el7            epel
stoken-libs.x86_64                    0.91-1.el7              epel
xlockmore.x86_64                      5.49-2.el7              epel
Obsoleting Packages
ddashboard.x86_64                     0.2.0.1-1.el7_3         mhlavink-developerdashboard
    developerdashboard.x86_64         0.1.12.2-1.el7_2        @mhlavink-developerdashboard
python-bugzilla.noarch                1.2.2-3.el7_2.1         mhlavink-developerdashboard
    python-bugzilla-develdashboardfixes.noarch
                                      1.2.2-3.el7             @mhlavink-developerdashboard
python2-futures.noarch                3.0.5-1.el7             epel
    python-futures.noarch             3.0.3-1.el7             @epel
python2-pip.noarch                    8.1.2-5.el7             epel
    python-pip.noarch                 7.1.0-1.el7             @epel
python2-pyxdg.noarch                  0.25-6.el7              epel
    pyxdg.noarch                      0.25-5.el7              @epel
python2-simplejson.x86_64             3.10.0-1.el7            epel
    python-simplejson.x86_64          3.3.3-1.el7             @epel
Security: kernel-3.10.0-327.28.2.el7.x86_64 is an installed security update
Security: kernel-3.10.0-327.22.2.el7.x86_64 is the currently running version
"""

# From https://github.com/ansible/ansible/issues/20608#issuecomment-276698431
wrapped_output_3 = """
Loaded plugins: fastestmirror, langpacks
Loading mirror speeds from cached hostfile

ceph.x86_64                               1:11.2.0-0.el7                    ceph
ceph-base.x86_64                          1:11.2.0-0.el7                    ceph
ceph-common.x86_64                        1:11.2.0-0.el7                    ceph
ceph-mds.x86_64                           1:11.2.0-0.el7                    ceph
ceph-mon.x86_64                           1:11.2.0-0.el7                    ceph
ceph-osd.x86_64                           1:11.2.0-0.el7                    ceph
ceph-selinux.x86_64                       1:11.2.0-0.el7                    ceph
libcephfs1.x86_64                         1:11.0.2-0.el7                    ceph
librados2.x86_64                          1:11.2.0-0.el7                    ceph
libradosstriper1.x86_64                   1:11.2.0-0.el7                    ceph
librbd1.x86_64                            1:11.2.0-0.el7                    ceph
librgw2.x86_64                            1:11.2.0-0.el7                    ceph
python-cephfs.x86_64                      1:11.2.0-0.el7                    ceph
python-rados.x86_64                       1:11.2.0-0.el7                    ceph
python-rbd.x86_64                         1:11.2.0-0.el7                    ceph
"""

# from https://github.com/ansible/ansible-modules-core/issues/4318#issuecomment-251416661
wrapped_output_4 = """
ipxe-roms-qemu.noarch                 20160127-1.git6366fa7a.el7
                                                            rhelosp-9.0-director-puddle
quota.x86_64                          1:4.01-11.el7_2.1     rhelosp-rhel-7.2-z
quota-nls.noarch                      1:4.01-11.el7_2.1     rhelosp-rhel-7.2-z
rdma.noarch                           7.2_4.1_rc6-2.el7     rhelosp-rhel-7.2-z
screen.x86_64                         4.1.0-0.23.20120314git3c2946.el7_2
                                                            rhelosp-rhel-7.2-z
sos.noarch                            3.2-36.el7ost.2       rhelosp-9.0-puddle
sssd-client.x86_64                    1.13.0-40.el7_2.12    rhelosp-rhel-7.2-z
"""


class TestYumUpdateCheckParse(unittest.TestCase):
    def _assert_expected(self, expected_pkgs, result):
        for expected_pkg in expected_pkgs:
            self.assertIn(expected_pkg, result)

    def test_plugin_load_error(self):
        res = yum.parse_check_update(yum_plugin_load_error)
        self.assertEqual(res, {})
        self.assertEqual(len(res), 0)

    def test_wrapped_output_1(self):
        res = yum.parse_check_update(wrapped_output_1)
        expected_pkgs = ["vms-agent"]
        self._assert_expected(expected_pkgs, res)

    def test_wrapped_output_2(self):
        res = yum.parse_check_update(wrapped_output_2)
        expected_pkgs = ["empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty-empty", "libtiff"]

        self._assert_expected(expected_pkgs, res)

    def test_wrapped_output_3(self):
        res = yum.parse_check_update(wrapped_output_3)
        expected_pkgs = ["ceph", "ceph-base", "ceph-common", "ceph-mds",
                        "ceph-mon", "ceph-osd", "ceph-selinux", "libcephfs1",
                        "librados2", "libradosstriper1", "librbd1", "librgw2",
                         "python-cephfs", "python-rados", "python-rbd"]
        self._assert_expected(expected_pkgs, res)

    def test_wrapped_output_4(self):
        res = yum.parse_check_update(wrapped_output_4)

        expected_pkgs = ["ipxe-roms-qemu"]
        self._assert_expected(expected_pkgs, res)

    def test_yum_check_update_output_rhel7(self):
        res = yum.parse_check_update(yum_check_update_output_rhel7)
        expected_pkgs = ["NetworkManager-openvpn", "xlockmore"]
        self._assert_expected(expected_pkgs, res)
