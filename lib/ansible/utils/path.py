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
from __future__ import annotations

import os
import shutil

from errno import EEXIST
from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text
from ansible.module_utils.common.file import unfrackpath


__all__ = ['unfrackpath', 'makedirs_safe']


def makedirs_safe(path, mode=None):
    '''
    A *potentially insecure* way to ensure the existence of a directory chain. The "safe" in this function's name
    refers only to its ability to ignore `EEXIST` in the case of multiple callers operating on the same part of
    the directory chain. This function is not safe to use under world-writable locations when the first level of the
    path to be created contains a predictable component. Always create a randomly-named element first if there is any
    chance the parent directory might be world-writable (eg, /tmp) to prevent symlink hijacking and potential
    disclosure or modification of sensitive file contents.

    :arg path: A byte or text string representing a directory chain to be created
    :kwarg mode: If given, the mode to set the directory to
    :raises AnsibleError: If the directory cannot be created and does not already exist.
    :raises UnicodeDecodeError: if the path is not decodable in the utf-8 encoding.
    '''

    rpath = unfrackpath(path)
    b_rpath = to_bytes(rpath)
    if not os.path.exists(b_rpath):
        try:
            if mode:
                os.makedirs(b_rpath, mode)
            else:
                os.makedirs(b_rpath)
        except OSError as e:
            if e.errno != EEXIST:
                raise AnsibleError("Unable to create local directories(%s): %s" % (to_native(rpath), to_native(e)))


def basedir(source):
    """ returns directory for inventory or playbook """
    source = to_bytes(source, errors='surrogate_or_strict')
    dname = None
    if os.path.isdir(source):
        dname = source
    elif source in [None, '', '.']:
        dname = os.getcwd()
    elif os.path.isfile(source):
        dname = os.path.dirname(source)

    if dname:
        # don't follow symlinks for basedir, enables source re-use
        dname = os.path.abspath(dname)

    return to_text(dname, errors='surrogate_or_strict')


def cleanup_tmp_file(path, warn=False):
    """
    Removes temporary file or directory. Optionally display a warning if unable
    to remove the file or directory.

    :arg path: Path to file or directory to be removed
    :kwarg warn: Whether or not to display a warning when the file or directory
        cannot be removed
    """
    try:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.unlink(path)
            except Exception as e:
                if warn:
                    # Importing here to avoid circular import
                    from ansible.utils.display import Display
                    display = Display()
                    display.display(u'Unable to remove temporary file {0}'.format(to_text(e)))
    except Exception:
        pass


def is_subpath(child, parent, real=False):
    """
    Compares paths to check if one is contained in the other
    :arg: child: Path to test
    :arg parent; Path to test against
     """
    test = False

    abs_child = unfrackpath(child, follow=False)
    abs_parent = unfrackpath(parent, follow=False)

    if real:
        abs_child = os.path.realpath(abs_child)
        abs_parent = os.path.realpath(abs_parent)

    c = abs_child.split(os.path.sep)
    p = abs_parent.split(os.path.sep)

    try:
        test = c[:len(p)] == p
    except IndexError:
        # child is shorter than parent so cannot be subpath
        pass

    return test
