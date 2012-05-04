# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
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
#

################################################

import multiprocessing
import signal
import os
import pwd
import Queue
import random
import traceback
import tempfile
import time
import base64
import getpass

import ansible.constants as C 
import ansible.connection
import ansible.inventory
from ansible import utils
from ansible import errors
from ansible import callbacks as ans_callbacks
    
HAS_ATFORK=True
try:
    from Crypto.Random import atfork
except ImportError:
    HAS_ATFORK=False

################################################

def _executor_hook(job_queue, result_queue):
    ''' callback used by multiprocessing pool '''

    # attempt workaround of https://github.com/newsapps/beeswithmachineguns/issues/17
    # does not occur for everyone, some claim still occurs on newer paramiko
    # this function not present in CentOS 6
    if HAS_ATFORK:
        atfork()

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    while not job_queue.empty():
        try:
            job = job_queue.get(block=False)
            runner, host = job
            result_queue.put(runner._executor(host))
        except Queue.Empty:
            pass
        except:
            traceback.print_exc()
 
################################################

class Runner(object):

    def __init__(self, 
        host_list=C.DEFAULT_HOST_LIST, module_path=C.DEFAULT_MODULE_PATH,
        module_name=C.DEFAULT_MODULE_NAME, module_args=C.DEFAULT_MODULE_ARGS, 
        forks=C.DEFAULT_FORKS, timeout=C.DEFAULT_TIMEOUT, 
        pattern=C.DEFAULT_PATTERN, remote_user=C.DEFAULT_REMOTE_USER, 
        remote_pass=C.DEFAULT_REMOTE_PASS, remote_port=C.DEFAULT_REMOTE_PORT, 
        sudo_pass=C.DEFAULT_SUDO_PASS, background=0, basedir=None, 
        setup_cache=None, transport=C.DEFAULT_TRANSPORT, conditional='True', 
        callbacks=None, debug=False, sudo=False, module_vars=None, 
        is_playbook=False, inventory=None):

        """
        host_list    : path to a host list file, like /etc/ansible/hosts
        module_path  : path to modules, like /usr/share/ansible
        module_name  : which module to run (string)
        module_args  : args to pass to the module (string)
        forks        : desired level of paralellism (hosts to run on at a time)
        timeout      : connection timeout, such as a SSH timeout, in seconds
        pattern      : pattern or groups to select from in inventory
        remote_user  : connect as this remote username
        remote_pass  : supply this password (if not using keys)
        remote_port  : use this default remote port (if not set by the inventory system)
        sudo_pass    : sudo password if using sudo and sudo requires a password
        background   : run asynchronously with a cap of this many # of seconds (if not 0)
        basedir      : paths used by modules if not absolute are relative to here
        setup_cache  : this is a internalism that is going away
        transport    : transport mode (paramiko, local)
        conditional  : only execute if this string, evaluated, is True
        callbacks    : output callback class
        sudo         : log in as remote user and immediately sudo to root
        module_vars  : provides additional variables to a template.  FIXME: just use module_args, remove
        is_playbook  : indicates Runner is being used by a playbook.  affects behavior in various ways.
        inventory    : inventory object, if host_list is not provided
        """

        if setup_cache is None:
            setup_cache = {}
        if basedir is None: 
            basedir = os.getcwd()

        if callbacks is None:
            callbacks = ans_callbacks.DefaultRunnerCallbacks()
        self.callbacks = callbacks

        self.generated_jid = str(random.randint(0, 999999999999))

        self.transport = transport
        self.connector = ansible.connection.Connection(self, self.transport)

        if inventory is None:
            self.inventory = ansible.inventory.Inventory(host_list)
        else:
            self.inventory = inventory

        if module_vars is None:
            module_vars = {}

        self.setup_cache = setup_cache
        self.conditional = conditional
        self.module_path = module_path
        self.module_name = module_name
        self.forks       = int(forks)
        self.pattern     = pattern
        self.module_args = module_args
        self.module_vars = module_vars
        self.timeout     = timeout
        self.debug       = debug
        self.remote_user = remote_user
        self.remote_pass = remote_pass
        self.remote_port = remote_port
        self.background  = background
        self.basedir     = basedir
        self.sudo        = sudo
        self.sudo_pass   = sudo_pass
        self.is_playbook = is_playbook

        euid = pwd.getpwuid(os.geteuid())[0]
        if self.transport == 'local' and self.remote_user != euid:
            raise Exception("User mismatch: expected %s, but is %s" % (self.remote_user, euid))
        if type(self.module_args) not in [str, unicode, dict]:
            raise Exception("module_args must be a string or dict: %s" % self.module_args)

        self._tmp_paths  = {}
        random.seed()

    # *****************************************************

    @classmethod
    def parse_hosts(cls, host_list, override_hosts=None):
        ''' parse the host inventory file, returns (hosts, groups) '''

        if override_hosts is None:
            inventory = ansible.inventory.Inventory(host_list)
        else:
            inventory = ansible.inventory.Inventory(override_hosts)

        return inventory.host_list, inventory.groups

    # *****************************************************

    def _return_from_module(self, conn, host, result, err, executed=None):
        ''' helper function to handle JSON parsing of results '''

        try:
            result = utils.parse_json(result) 
            if executed is not None:
                result['invocation'] = executed
                if 'stderr' in result:
                    err="%s%s"%(err,result['stderr'])
            return [host, True, result, err]
        except Exception, e:
            return [host, False, "%s/%s/%s" % (str(e), result, executed), err]

    # *****************************************************

    def _delete_remote_files(self, conn, files):
        ''' deletes one or more remote files '''

        if type(files) == str:
            files = [ files ]
        for filename in files:
            if filename.find('/tmp/') == -1:
                raise Exception("not going to happen")
            self._exec_command(conn, "rm -rf %s" % filename, None)

    # *****************************************************

    def _transfer_module(self, conn, tmp, module):
        ''' transfers a module file to the remote side to execute it, but does not execute it yet '''

        outpath = self._copy_module(conn, tmp, module)
        self._exec_command(conn, "chmod +x %s" % outpath, tmp)
        return outpath

    # *****************************************************

    def _transfer_str(self, conn, tmp, name, data):
        ''' transfer string to remote file '''

        if type(data) == dict:
            data = utils.smjson(data)

        afd, afile = tempfile.mkstemp()
        afo = os.fdopen(afd, 'w')
        afo.write(data)
        afo.flush()
        afo.close()

        remote = os.path.join(tmp, name)
        conn.put_file(afile, remote)
        os.unlink(afile)
        return remote

    # *****************************************************

    def _add_setup_vars(self, inject, args):
        ''' setup module variables need special handling '''

        is_dict = False
        if type(args) == dict:
            is_dict = True

        # TODO: keep this as a dict through the whole path to simplify this code
        for (k,v) in inject.iteritems():
            if not k.startswith('facter_') and not k.startswith('ohai_') and not k.startswith('ansible_'):
                if not is_dict:
                    if str(v).find(" ") != -1:
                        v = "\"%s\"" % v
                    args += " %s=%s" % (k, str(v).replace(" ","~~~"))
                else:
                    args[k]=v
        return args   
 
    # *****************************************************

    def _add_setup_metadata(self, args):
        ''' automatically determine where to store variables for the setup module '''
        
        is_dict = False
        if type(args) == dict:
            is_dict = True

        # TODO: keep this as a dict through the whole path to simplify this code
        if not is_dict:
            if args.find("metadata=") == -1:
                if self.remote_user == 'root':
                    args = "%s metadata=/etc/ansible/setup" % args
                else:
                    args = "%s metadata=$HOME/.ansible/setup" % args
        else:
            if not 'metadata' in args:
                if self.remote_user == 'root':
                    args['metadata'] = '/etc/ansible/setup'
                else:
                    args['metadata'] = "$HOME/.ansible/setup"
        return args   
 
    # *****************************************************

    def _execute_module(self, conn, tmp, remote_module_path, args, 
        async_jid=None, async_module=None, async_limit=None):
        ''' runs a module that has already been transferred '''

        inject = self.setup_cache.get(conn.host,{})
        conditional = utils.double_template(self.conditional, inject, self.setup_cache)
        if not eval(conditional):
            return [ utils.smjson(dict(skipped=True)), None, 'skipped' ]

        host_variables = self.inventory.get_variables(conn.host)
        inject.update(host_variables)

        if self.module_name == 'setup':
            args = self._add_setup_vars(inject, args)
            args = self._add_setup_metadata(args)

        if type(args) == dict:
            args = utils.bigjson(args)
        args = utils.template(args, inject, self.setup_cache)

        module_name_tail = remote_module_path.split("/")[-1]

        argsfile = self._transfer_str(conn, tmp, 'arguments', args)
        if async_jid is None:
            cmd = "%s %s" % (remote_module_path, argsfile)
        else:
            cmd = " ".join([str(x) for x in [remote_module_path, async_jid, async_limit, async_module, argsfile]])

        res, err = self._exec_command(conn, cmd, tmp, sudoable=True)
        client_executed_str = "%s %s" % (module_name_tail, args.strip())
        return ( res, err, client_executed_str )

    # *****************************************************

    def _save_setup_result_to_disk(self, conn, result):
       ''' cache results of calling setup '''

       dest = os.path.expanduser("~/.ansible_setup_data")
       user = getpass.getuser()
       if user == 'root':
           dest = "/var/lib/ansible/setup_data"
       if not os.path.exists(dest):
           os.makedirs(dest)

       fh = open(os.path.join(dest, conn.host), "w")
       fh.write(result)
       fh.close()

       return result

    # *****************************************************

    def _add_result_to_setup_cache(self, conn, result):
        ''' allows discovered variables to be used in templates and action statements '''

        host = conn.host
        if 'ansible_facts' in result:
            var_result = result['ansible_facts']
        else:
            var_result = {}

        # note: do not allow variables from playbook to be stomped on
        # by variables coming up from facter/ohai/etc.  They
        # should be prefixed anyway
        if not host in self.setup_cache:
            self.setup_cache[host] = {}
        for (k, v) in var_result.iteritems():
            if not k in self.setup_cache[host]:
                self.setup_cache[host][k] = v

    # *****************************************************

    def _execute_normal_module(self, conn, host, tmp, module_name):
        ''' transfer & execute a module that is not 'copy' or 'template' '''

        # shell and command are the same module
        if module_name == 'shell':
            module_name = 'command'
            self.module_args += " #USE_SHELL"

        module = self._transfer_module(conn, tmp, module_name)
        (result, err, executed) = self._execute_module(conn, tmp, module, self.module_args)

        (host, ok, data, err) = self._return_from_module(conn, host, result, err, executed)

        if ok:
            self._add_result_to_setup_cache(conn, data)

        return (host, ok, data, err)

    # *****************************************************

    def _execute_async_module(self, conn, host, tmp, module_name):
        ''' transfer the given module name, plus the async module, then run it '''

        # hack to make the 'shell' module keyword really be executed
        # by the command module
        module_args = self.module_args
        if module_name == 'shell':
            module_name = 'command'
            module_args += " #USE_SHELL"

        async  = self._transfer_module(conn, tmp, 'async_wrapper')
        module = self._transfer_module(conn, tmp, module_name)
        (result, err, executed) = self._execute_module(conn, tmp, async, module_args,
           async_module=module, 
           async_jid=self.generated_jid, 
           async_limit=self.background
        )

        return self._return_from_module(conn, host, result, err, executed)

    # *****************************************************

    def _execute_copy(self, conn, host, tmp):
        ''' handler for file transfer operations '''

        # load up options
        options = utils.parse_kv(self.module_args)
        source = options.get('src', None)
        dest   = options.get('dest', None)
        if (source is None and not 'first_available_file' in self.module_vars) or dest is None:
            return (host, True, dict(failed=True, msg="src and dest are required"), '')

        # apply templating to source argument
        inject = self.setup_cache.get(conn.host,{})
        
        # FIXME: break duplicate code up into subfunction
        # if we have first_available_file in our vars
        # look up the files and use the first one we find as src
        if 'first_available_file' in self.module_vars:
            found = False
            for fn in self.module_vars.get('first_available_file'):
                fn = utils.template(fn, inject, self.setup_cache)
                if os.path.exists(fn):
                    source = fn
                    found = True
                    break
            if not found:
                return (host, True, dict(failed=True, msg="could not find src in first_available_file list"), '')
        
        source = utils.template(source, inject, self.setup_cache)

        # transfer the file to a remote tmp location
        tmp_src = tmp + source.split('/')[-1]
        conn.put_file(utils.path_dwim(self.basedir, source), tmp_src)

        # install the copy  module
        self.module_name = 'copy'
        module = self._transfer_module(conn, tmp, 'copy')

        # run the copy module
        args = "src=%s dest=%s" % (tmp_src, dest)
        (result1, err, executed) = self._execute_module(conn, tmp, module, args)
        (host, ok, data, err) = self._return_from_module(conn, host, result1, err, executed)

        if ok:
            return self._chain_file_module(conn, tmp, data, err, options, executed)
        else:
            return (host, ok, data, err) 

    # *****************************************************

    def _execute_fetch(self, conn, host, tmp):
        ''' handler for fetch operations '''

        # load up options
        options = utils.parse_kv(self.module_args)
        source = options.get('src', None)
        dest = options.get('dest', None)
        if source is None or dest is None:
            return (host, True, dict(failed=True, msg="src and dest are required"), '')

        # files are saved in dest dir, with a subdir for each host, then the filename
        dest   = "%s/%s/%s" % (utils.path_dwim(self.basedir, dest), host, source)
        dest   = dest.replace("//","/")

        # compare old and new md5 for support of change hooks
        local_md5 = None
        if os.path.exists(dest):
            local_md5 = os.popen("md5sum %s" % dest).read().split()[0]
        remote_md5 = self._exec_command(conn, "md5sum %s" % source, tmp, True)[0].split()[0]

        if remote_md5 != local_md5:
            # create the containing directories, if needed
            os.makedirs(os.path.dirname(dest))
            # fetch the file and check for changes
            conn.fetch_file(source, dest)
            new_md5 = os.popen("md5sum %s" % dest).read().split()[0]
            if new_md5 != remote_md5:
                return (host, True, dict(failed=True, msg="md5 mismatch", md5sum=new_md5), '')
            return (host, True, dict(changed=True, md5sum=new_md5), '')
        else:
            return (host, True, dict(changed=False, md5sum=local_md5), '')
        
        
    # *****************************************************

    def _chain_file_module(self, conn, tmp, data, err, options, executed):
        ''' handles changing file attribs after copy/template operations '''

        old_changed = data.get('changed', False)
        module = self._transfer_module(conn, tmp, 'file')
        args = ' '.join([ "%s=%s" % (k,v) for (k,v) in options.items() ])
        (result2, err2, executed2) = self._execute_module(conn, tmp, module, args)
        results2 = self._return_from_module(conn, conn.host, result2, err2, executed)
        (host, ok, data2, err2) = results2
        if ok:
            new_changed = data2.get('changed', False)
            data.update(data2)
        else:
            new_changed = False
        if old_changed or new_changed:
            data['changed'] = True
        return (host, ok, data, "%s%s"%(err,err2))

    # *****************************************************

    def _execute_template(self, conn, host, tmp):
        ''' handler for template operations '''

        # load up options
        options  = utils.parse_kv(self.module_args)
        source   = options.get('src', None)
        dest     = options.get('dest', None)
        metadata = options.get('metadata', None)
        if (source is None and 'first_available_file' not in self.module_vars) or dest is None:
            return (host, True, dict(failed=True, msg="src and dest are required"), '')

        # apply templating to source argument so vars can be used in the path
        inject = self.setup_cache.get(conn.host,{})

        # if we have first_available_file in our vars
        # look up the files and use the first one we find as src
        if 'first_available_file' in self.module_vars:
            found = False
            for fn in self.module_vars.get('first_available_file'):
                fn = utils.template(fn, inject, self.setup_cache)
                if os.path.exists(fn):
                    source = fn
                    found = True
                    break
            if not found:
                return (host, True, dict(failed=True, msg="could not find src in first_available_file list"), '')

        source = utils.template(source, inject, self.setup_cache)

        (host, ok, data, err) = (None, None, None, None)

        if not self.is_playbook:

            # not running from a playbook so we have to fetch the remote
            # setup file contents before proceeding...
            if metadata is None:
                if self.remote_user == 'root':
                    metadata = '/etc/ansible/setup'
                else:
                    # path is expanded on remote side
                    metadata = "~/.ansible/setup"
            
            # install the template module
            slurp_module = self._transfer_module(conn, tmp, 'slurp')

            # run the slurp module to get the metadata file
            args = "src=%s" % metadata
            (result1, err, executed) = self._execute_module(conn, tmp, slurp_module, args)
            result1 = utils.json_loads(result1)
            if not 'content' in result1 or result1.get('encoding','base64') != 'base64':
                result1['failed'] = True
                return self._return_from_module(conn, host, result1, err, executed)
            content = base64.b64decode(result1['content'])
            inject = utils.json_loads(content)

        # install the template module
        copy_module = self._transfer_module(conn, tmp, 'copy')

        # template the source data locally
        source_data = file(utils.path_dwim(self.basedir, source)).read()
        resultant = ''            
        try:
            resultant = utils.template(source_data, inject, self.setup_cache)
        except Exception, e:
            return (host, False, dict(failed=True, msg=str(e)), '')
        xfered = self._transfer_str(conn, tmp, 'source', resultant)
            
        # run the COPY module
        args = "src=%s dest=%s" % (xfered, dest)
        (result1, err, executed) = self._execute_module(conn, tmp, copy_module, args)
        (host, ok, data, err) = self._return_from_module(conn, host, result1, err, executed)
 
        # modify file attribs if needed
        if ok:
            executed = executed.replace("copy","template",1)
            return self._chain_file_module(conn, tmp, data, err, options, executed)
        else:
            return (host, ok, data, err)

    # *****************************************************

    def _executor(self, host):
        try:
            (host, ok, data, err) = self._executor_internal(host)
            if not ok:
                self.callbacks.on_unreachable(host, data)
            return (host, ok, data)
        except errors.AnsibleError, ae:
            msg = str(ae)
            self.callbacks.on_unreachable(host, msg)
            return [host, False, msg]
        except Exception:
            msg = traceback.format_exc()
            self.callbacks.on_unreachable(host, msg)
            return [host, False, msg]

    def _executor_internal(self, host):
        ''' callback executed in parallel for each host. returns (hostname, connected_ok, extra) '''

        host_variables = self.inventory.get_variables(host)
        port = host_variables.get('ansible_ssh_port', self.remote_port)

        conn = None
        try:
            conn = self.connector.connect(host, port)
        except errors.AnsibleConnectionFailed, e:
            return [ host, False, "FAILED: %s" % str(e), None ]

        cache = self.setup_cache.get(host, {})
        module_name = utils.template(self.module_name, cache, self.setup_cache)

        tmp = self._get_tmp_path(conn)
        result = None

        if self.module_name == 'copy':
            result = self._execute_copy(conn, host, tmp)
        elif self.module_name == 'fetch':
            result = self._execute_fetch(conn, host, tmp)
        elif self.module_name == 'template':
            result = self._execute_template(conn, host, tmp)
        else:
            if self.background == 0:
                result = self._execute_normal_module(conn, host, tmp, module_name)
            else:
                result = self._execute_async_module(conn, host, tmp, module_name)

        self._delete_remote_files(conn, tmp)
        conn.close()

        (host, connect_ok, data, err) = result
        if not connect_ok:
            self.callbacks.on_unreachable(host, data)
        else:
            if 'failed' in data or 'rc' in data and str(data['rc']) != '0':
                self.callbacks.on_failed(host, data)
            elif 'skipped' in data:
                self.callbacks.on_skipped(host)
            else:
                self.callbacks.on_ok(host, data)

            if err:
                if self.debug or data.get('parsed', True) == False:
                    self.callbacks.on_error(host, err)

        return result

    # *****************************************************

    def _exec_command(self, conn, cmd, tmp, sudoable=False):
        ''' execute a command string over SSH, return the output '''

        stdin, stdout, stderr = conn.exec_command(cmd, tmp, sudoable=sudoable)
        err=None
        out=None
        if type(stderr) != str:
            err="\n".join(stderr.readlines())
        else:
            err=stderr
        if type(stdout) != str:
            out="\n".join(stdout.readlines())
        else:
            out=stdout
        return (out,err) 


    # *****************************************************

    def _get_tmp_path(self, conn):
        ''' gets a temporary path on a remote box '''

        # The problem with this is that it's executed on the
        # overlord, not on the target so we can't use tempdir and os.path
        # Only support the *nix world for now by using the $HOME env var

        basetmp = "/var/tmp"
        if self.remote_user != 'root':
            basetmp = "$HOME/.ansible/tmp"
        cmd = "mktemp -d %s/ansible.XXXXXX" % basetmp
        if self.remote_user != 'root':
            cmd = "mkdir -p %s && %s" % (basetmp, cmd)

        result, err = self._exec_command(conn, cmd, None, sudoable=False)
        cleaned = result.split("\n")[0].strip() + '/'
        return cleaned


    # *****************************************************

    def _copy_module(self, conn, tmp, module):
        ''' transfer a module over SFTP, does not run it '''

        if module.startswith("/"):
            raise errors.AnsibleFileNotFound("%s is not a module" % module)
        in_path = os.path.expanduser(os.path.join(self.module_path, module))
        if not os.path.exists(in_path):
            raise errors.AnsibleFileNotFound("module not found: %s" % in_path)

        out_path = tmp + module
        conn.put_file(in_path, out_path)
        return out_path

    # *****************************************************

    def _parallel_exec(self, hosts):
        ''' handles mulitprocessing when more than 1 fork is required '''

        job_queue = multiprocessing.Manager().Queue()
        [job_queue.put(i) for i in hosts]

        result_queue = multiprocessing.Manager().Queue()

        workers = []
        for i in range(self.forks):
            prc = multiprocessing.Process(target=_executor_hook,
                args=(job_queue, result_queue))
            prc.start()
            workers.append(prc)

        try:
            for worker in workers:
                worker.join()
        except KeyboardInterrupt:
            for worker in workers:
                worker.terminate()
                worker.join()

        results = []
        while not result_queue.empty():
            results.append(result_queue.get(block=False))
        return results

    # *****************************************************

    def _partition_results(self, results):
        ''' seperate results by ones we contacted & ones we didn't '''

        results2 = dict(contacted={}, dark={})

        if results is None:
            return None

        for result in results:
            (host, contacted_ok, result) = result
            if contacted_ok:
                results2["contacted"][host] = result
            else:
                results2["dark"][host] = result

        # hosts which were contacted but never got a chance to return
        for host in self.inventory.list_hosts(self.pattern):
            if not (host in results2['dark'] or host in results2['contacted']):
                results2["dark"][host] = {}

        return results2

    # *****************************************************

    def run(self):
        ''' xfer & run module on all matched hosts '''
       
        # find hosts that match the pattern
        hosts = self.inventory.list_hosts(self.pattern)
        if len(hosts) == 0:
            self.callbacks.on_no_hosts()
            return dict(contacted={}, dark={})
 
        hosts = [ (self,x) for x in hosts ]
        results = None
        if self.forks > 1:
            results = self._parallel_exec(hosts)
        else:
            results = [ self._executor(h[1]) for h in hosts ]
        return self._partition_results(results)

    def runAsync(self, time_limit):
        ''' Run this module asynchronously and return a poller. '''
        self.background = time_limit
        results = self.run()

        return results, AsyncPoller(results, self)

class AsyncPoller(object):
    """ Manage asynchronous jobs. """

    def __init__(self, results, runner):
        self.runner = runner

        self.results = { 'contacted': {}, 'dark': {}}
        self.hosts_to_poll = []
        self.completed = False

        # Get job id and which hosts to poll again in the future
        jid = None
        for (host, res) in results['contacted'].iteritems():
            if res.get('started', False):
                self.hosts_to_poll.append(host)
                jid = res.get('ansible_job_id', None)
            else:
                self.results['contacted'][host] = res
        for (host, res) in results['dark'].iteritems():
            self.results['dark'][host] = res

        if jid is None:
            raise errors.AnsibleError("unexpected error: unable to determine jid")
        if len(self.hosts_to_poll)==0:
            raise errors.AnsibleErrot("unexpected error: no hosts to poll")
        self.jid = jid

    def poll(self):
        """ Poll the job status.

            Returns the changes in this iteration."""
        self.runner.module_name = 'async_status'
        self.runner.module_args = "jid=%s" % self.jid
        self.runner.pattern = "*"
        self.runner.background = 0

        self.runner.inventory.restrict_to(self.hosts_to_poll)
        results = self.runner.run()
        self.runner.inventory.lift_restriction()

        hosts = []
        poll_results = { 'contacted': {}, 'dark': {}, 'polled': {}}
        for (host, res) in results['contacted'].iteritems():
            if res.get('started',False):
                hosts.append(host)
                poll_results['polled'][host] = res
            else:
                self.results['contacted'][host] = res
                poll_results['contacted'][host] = res
                if 'failed' in res:
                    self.runner.callbacks.on_async_failed(host, res, self.jid)
                else:
                    self.runner.callbacks.on_async_ok(host, res, self.jid)
        for (host, res) in results['dark'].iteritems():
            self.results['dark'][host] = res
            poll_results['dark'][host] = res
            self.runner.callbacks.on_async_failed(host, res, self.jid)

        self.hosts_to_poll = hosts
        if len(hosts)==0:
            self.completed = True

        return poll_results

    def wait(self, seconds, poll_interval):
        """ Wait a certain time for job completion, check status every poll_interval. """
        clock = seconds - poll_interval
        while (clock >= 0 and not self.completed):
            time.sleep(poll_interval)

            poll_results = self.poll()

            for (host, res) in poll_results['polled'].iteritems():
                if res.get('started'):
                    self.runner.callbacks.on_async_poll(host, res, self.jid, clock)

            clock = clock - poll_interval

        return self.results
