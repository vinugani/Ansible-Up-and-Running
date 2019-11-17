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

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import cmd
import functools
import os
import pickle
import pprint
import random
import string
import sys
import tempfile
import time

from multiprocessing import Lock
from jinja2.exceptions import UndefinedError

from ansible import constants as C
from ansible import context
from ansible.errors import AnsibleError, AnsibleFileNotFound, AnsibleParserError, AnsibleUndefinedVariable
from ansible.executor import action_write_locks
from ansible.executor.task_result import TaskResult
from ansible.inventory.host import Host
from ansible.module_utils.six.moves import queue as Queue
from ansible.module_utils.six import iteritems, itervalues, string_types
from ansible.module_utils._text import to_text
from ansible.module_utils.connection import Connection, ConnectionError
from ansible.playbook.base import post_validate
from ansible.playbook.conditional import evaluate_conditional
from ansible.playbook.helpers import load_list_of_blocks
from ansible.playbook.included_file import IncludedFile
from ansible.playbook.play_context import set_task_and_variable_override
from ansible.playbook.task_include import TaskInclude
from ansible.plugins import loader as plugin_loader
from ansible.template import Templar
from ansible.utils.display import Display
from ansible.utils.inventory import add_host, add_group
from ansible.utils.path import unfrackpath
from ansible.vars.clean import strip_internal_keys, module_response_deepcopy

display = Display()

__all__ = ['StrategyBase']


def SharedPluginLoaderObj():
    '''This only exists for backwards compat, do not use.
    '''
    display.deprecated('SharedPluginLoaderObj is deprecated, please directly use ansible.plugins.loader',
                       version='2.11')
    return plugin_loader


def debug_closure(func):
    """Closure to wrap ``StrategyBase._process_pending_results`` and invoke the task debugger"""
    @functools.wraps(func)
    def inner(self, iterator, one_pass=False, max_passes=None):
        status_to_stats_map = (
            ('is_failed', 'failures'),
            ('is_unreachable', 'dark'),
            ('is_changed', 'changed'),
            ('is_skipped', 'skipped'),
        )

        # We don't know the host yet, copy the previous states, for lookup after we process new results
        prev_host_states = iterator._host_states.copy()

        results = func(self, iterator, one_pass=one_pass, max_passes=max_passes)
        _processed_results = []

        for result in results:
            _queued_task_args = self._queued_task_cache.pop((result['host_name'], result['task_uuid']), None)
            host = _queued_task_args['host']
            task = _queued_task_args['task']
            task_vars = _queued_task_args['task_vars']
            play_context = _queued_task_args['play_context']
            # Try to grab the previous host state, if it doesn't exist use get_host_state to generate an empty state
            try:
                prev_host_state = prev_host_states[host.name]
            except KeyError:
                prev_host_state = iterator.get_host_state(host)
            while result.get('needs_debug', False):
                next_action = NextAction()
                # FIXME: debugger is expecting a task result, not a host status update...
                #        so this is not working yet
                dbg = Debugger(task, host, task_vars, play_context, result, next_action)
                dbg.cmdloop()
                if next_action.result == NextAction.REDO:
                    # rollback host state
                    self._tqm.clear_failed_hosts()
                    iterator._host_states[host.name] = prev_host_state
                    for method, what in status_to_stats_map:
                        if getattr(result, method)():
                            self._tqm._stats.decrement(what, host.name)
                    self._tqm._stats.decrement('ok', host.name)
                    # redo
                    self._queue_task(host, task, task_vars, play_context)
                    _processed_results.extend(debug_closure(func)(self, iterator, one_pass))
                    break
                elif next_action.result == NextAction.CONTINUE:
                    _processed_results.append(result)
                    break
                elif next_action.result == NextAction.EXIT:
                    # Matches KeyboardInterrupt from bin/ansible
                    sys.exit(99)
            else:
                _processed_results.append(result)
        return _processed_results
    return inner


class StrategyBase:

    '''
    This is the base class for strategy plugins, which contains some common
    code useful to all strategies like running handlers, cleanup actions, etc.
    '''

    # by default, strategies should support throttling but we allow individual
    # strategies to disable this and either forego supporting it or managing
    # the throttling internally (as `free` does)
    ALLOW_BASE_THROTTLING = True

    def __init__(self, tqm):
        self._tqm = tqm
        self._inventory = tqm.get_inventory()
        self._workers = tqm._workers
        self._variable_manager = tqm.get_variable_manager()
        self._loader = tqm.get_loader()
        self._final_q = tqm._final_q
        self._step = context.CLIARGS.get('step', False)
        self._diff = context.CLIARGS.get('diff', False)
        self.flush_cache = context.CLIARGS.get('flush_cache', False)

        # the task cache is a dictionary of tuples of (host.name, task._uuid)
        # used to find the original task object of in-flight tasks and to store
        # the task args/vars and play context info used to queue the task.
        self._queued_task_cache = {}

        # Backwards compat: self._display isn't really needed, just import the global display and use that.
        self._display = display

        # internal counters
        self._pending_results = 0
        self._cur_worker = 0

        # this dictionary is used to keep track of hosts that have
        # outstanding tasks still in queue
        self._blocked_hosts = dict()

        # this dictionary is used to keep track of hosts that have
        # flushed handlers
        self._flushed_hosts = dict()

        # holds the list of active (persistent) connections to be shutdown at
        # play completion
        self._active_connections = dict()

        # Caches for get_host calls, to avoid calling excessively
        # These values should be set at the top of the ``run`` method of each
        # strategy plugin. Use ``_set_hosts_cache`` to set these values
        self._hosts_cache = []
        self._hosts_cache_all = []

        self.debugger_active = C.ENABLE_TASK_DEBUGGER

        self._worker_update_list = []
        self._worker_update_lock = Lock()

    def _set_hosts_cache(self, play, refresh=True):
        """Responsible for setting _hosts_cache and _hosts_cache_all

        See comment in ``__init__`` for the purpose of these caches
        """
        if not refresh and all((self._hosts_cache, self._hosts_cache_all)):
            return

        if Templar(None).is_template(play.hosts):
            _pattern = 'all'
        else:
            _pattern = play.hosts or 'all'
        self._hosts_cache_all = [h.name for h in self._inventory.get_hosts(pattern=_pattern, ignore_restrictions=True)]
        self._hosts_cache = [h.name for h in self._inventory.get_hosts(play.hosts, order=play.order)]

    def cleanup(self):
        # close active persistent connections
        for sock in itervalues(self._active_connections):
            try:
                conn = Connection(sock)
                conn.reset()
            except ConnectionError as e:
                # most likely socket is already closed
                display.debug("got an error while closing persistent connection: %s" % e)

    def run(self, iterator, play_context, result=0):
        # execute one more pass through the iterator without peeking, to
        # make sure that all of the hosts are advanced to their final task.
        # This should be safe, as everything should be ITERATING_COMPLETE by
        # this point, though the strategy may not advance the hosts itself.

        for host in self._hosts_cache:
            if host not in self._tqm._unreachable_hosts:
                try:
                    iterator.get_next_task_for_host(self._inventory.hosts[host])
                except KeyError:
                    iterator.get_next_task_for_host(self._inventory.get_host(host))

        # save the failed/unreachable hosts, as the run_handlers()
        # method will clear that information during its execution
        failed_hosts = iterator.get_failed_hosts()
        unreachable_hosts = self._tqm._unreachable_hosts.keys()

        display.debug("running handlers")
        handler_result = self.run_handlers(iterator, play_context)
        if isinstance(handler_result, bool) and not handler_result:
            result |= self._tqm.RUN_ERROR
        elif not handler_result:
            result |= handler_result

        # now update with the hosts (if any) that failed or were
        # unreachable during the handler execution phase
        failed_hosts = set(failed_hosts).union(iterator.get_failed_hosts())
        unreachable_hosts = set(unreachable_hosts).union(self._tqm._unreachable_hosts.keys())

        # return the appropriate code, depending on the status hosts after the run
        if not isinstance(result, bool) and result != self._tqm.RUN_OK:
            return result
        elif len(unreachable_hosts) > 0:
            return self._tqm.RUN_UNREACHABLE_HOSTS
        elif len(failed_hosts) > 0:
            return self._tqm.RUN_FAILED_HOSTS
        else:
            return self._tqm.RUN_OK

    def get_hosts_remaining(self, play):
        self._set_hosts_cache(play, refresh=False)
        ignore = set(self._tqm._failed_hosts).union(self._tqm._unreachable_hosts)
        return [host for host in self._hosts_cache if host not in ignore]

    def get_failed_hosts(self, play):
        self._set_hosts_cache(play, refresh=False)
        return [host for host in self._hosts_cache if host in self._tqm._failed_hosts]

    def add_tqm_variables(self, vars, play):
        '''
        Base class method to add extra variables/information to the list of task
        vars sent through the executor engine regarding the task queue manager state.
        '''
        vars['ansible_current_hosts'] = self.get_hosts_remaining(play)
        vars['ansible_failed_hosts'] = self.get_failed_hosts(play)

    def _queue_task(self, host, task, task_vars, play_context):
        ''' handles queueing the task up to be sent to a worker '''

        display.debug("entering _queue_task() for %s/%s" % (host.name, task.action))

        # Add a write lock for tasks.
        # Maybe this should be added somewhere further up the call stack but
        # this is the earliest in the code where we have task (1) extracted
        # into its own variable and (2) there's only a single code path
        # leading to the module being run.  This is called by three
        # functions: __init__.py::_do_handler_run(), linear.py::run(), and
        # free.py::run() so we'd have to add to all three to do it there.
        # The next common higher level is __init__.py::run() and that has
        # tasks inside of play_iterator so we'd have to extract them to do it
        # there.

        if task.action not in action_write_locks.action_write_locks:
            display.debug('Creating lock for %s' % task.action)
            action_write_locks.action_write_locks[task.action] = Lock()

        # create a templar and template things we need later for the queuing process
        templar = Templar(loader=self._loader, variables=task_vars)

        try:
            throttle = int(templar.template(task.throttle))
        except Exception as e:
            raise AnsibleError("Failed to convert the throttle value to an integer.", obj=task._ds, orig_exc=e)

        try:
            display.debug("adding host/task info to queued task cache")
            self._queued_task_cache[(host.name, task._uuid)] = {
                'host': host,
                'task': task,
                'task_vars': task_vars,
                'play_context': play_context
            }
            display.debug("done adding host/task info to queued task cache")
            display.debug("copying/squashing task and play context for queue")
            display.debug("done copying/squashing task and play context for queue")
            display.debug("putting the task/etc. in the queue")

            vars_path = os.path.join(
                C.DEFAULT_LOCAL_TMP,
                "vars-%05d-%s" % (self._cur_worker, ''.join(random.choice(string.ascii_lowercase) for i in range(10)))
            )
            with open(vars_path, 'wb') as f:
                pickle.dump(task_vars, f, pickle.HIGHEST_PROTOCOL)

            worker_update = []
            w_entry = self._workers[self._cur_worker]
            with self._worker_update_lock:
                if w_entry.last_update != len(self._worker_update_list):
                    # we take the slice of the update list we haven't sent
                    # to this worker yet, then save the len for next time
                    worker_update = self._worker_update_list[w_entry.last_update:len(self._worker_update_list)]
                    self._workers[self._cur_worker] = w_entry._replace(last_update=len(self._worker_update_list))

            w_entry.queue.put((host.serialize(), task.serialize(), play_context.serialize(), vars_path, worker_update), block=True)

            display.debug("done putting the task/etc. in the queue")
            self._cur_worker += 1

            rewind_point = len(self._workers)
            if throttle > 0 and self.ALLOW_BASE_THROTTLING:
                if task.run_once:
                    display.debug("Ignoring 'throttle' as 'run_once' is also set for '%s'" % task.get_name())
                else:
                    if throttle <= rewind_point:
                        display.debug("task: %s, throttle: %d" % (task.get_name(), throttle))
                        rewind_point = throttle

            if self._cur_worker >= rewind_point:
                self._cur_worker = 0
            self._pending_results += 1
        except (EOFError, IOError, AssertionError) as e:
            # most likely an abort
            display.debug("got an error while queuing: %s" % e)
            return

        display.debug("exiting _queue_task() for %s/%s" % (host.name, task.action))

    def get_task_hosts(self, iterator, task_host, task):
        if task.run_once:
            host_list = [host for host in self._hosts_cache if host not in self._tqm._unreachable_hosts]
        else:
            host_list = [task_host.name]
        return host_list

    def get_delegated_hosts(self, result, task):
        host_name = result.get('_ansible_delegated_vars', {}).get('ansible_delegated_host', None)
        return [host_name or task.delegate_to]

    @debug_closure
    def _process_pending_results(self, iterator, one_pass=False, max_passes=None):
        '''
        Reads results off the final queue and takes appropriate action
        based on the result (executing callbacks, updating state, etc.).
        '''
        try:
            host_status = self._tqm._results_q.get(block=False)
            cache_entry = self._queued_task_cache[(host_status['host_name'], host_status['task_uuid'])]
            original_host = cache_entry['host']
            original_task = cache_entry['task']

            # register any variables from the task
            if original_task.register:
                host_list = self.get_task_hosts(iterator, original_host, original_task)
                clean_copy = strip_internal_keys(module_response_deepcopy(host_status['original_result']))
                if 'invocation' in clean_copy:
                    del clean_copy['invocation']
                for target_host in host_list:
                    self._variable_manager.set_nonpersistent_facts(target_host, {original_task.register: clean_copy})

            if host_status['status_type'] == 'ok':
                self._tqm._stats.increment("ok", host_status["host_name"])
                if host_status['changed']:
                    self._tqm._stats.increment("changed", host_status["host_name"])
                if original_task.loop:
                    # this task had a loop, and has more than one result, so
                    # loop over all of them instead of a single result
                    result_items = host_status['original_result'].get('results', [])
                else:
                    result_items = [host_status['original_result']]

                for result_item in result_items:
                    if 'ansible_facts' in result_item:
                        # if delegated fact and we are delegating facts, we need to change target host for them
                        if original_task.delegate_to is not None and original_task.delegate_facts:
                            host_list = self.get_delegated_hosts(result_item, original_task)
                        else:
                            host_list = self.get_task_hosts(iterator, original_host, original_task)

                        if original_task.action == 'include_vars':
                            for (var_name, var_value) in iteritems(result_item['ansible_facts']):
                                # find the host we're actually referring too here, which may
                                # be a host that is not really in inventory at all
                                for target_host in host_list:
                                    self._variable_manager.set_host_variable(target_host, var_name, var_value)
                        else:
                            cacheable = result_item.pop('_ansible_facts_cacheable', False)
                            for target_host in host_list:
                                # so set_fact is a misnomer but 'cacheable = true' was meant to create an 'actual fact'
                                # to avoid issues with precedence and confusion with set_fact normal operation,
                                # we set BOTH fact and nonpersistent_facts (aka hostvar)
                                # when fact is retrieved from cache in subsequent operations it will have the lower precedence,
                                # but for playbook setting it the 'higher' precedence is kept
                                if original_task.action != 'set_fact' or cacheable:
                                    self._variable_manager.set_host_facts(target_host, result_item['ansible_facts'].copy())
                                if original_task.action == 'set_fact':
                                    self._variable_manager.set_nonpersistent_facts(target_host, result_item['ansible_facts'].copy())

                    if 'ansible_stats' in result_item and 'data' in result_item['ansible_stats'] and result_item['ansible_stats']['data']:
                        if 'per_host' not in result_item['ansible_stats'] or result_item['ansible_stats']['per_host']:
                            host_list = self.get_task_hosts(iterator, original_host, original_task)
                        else:
                            host_list = [None]

                        data = result_item['ansible_stats']['data']
                        aggregate = 'aggregate' in result_item['ansible_stats'] and result_item['ansible_stats']['aggregate']
                        for myhost in host_list:
                            for k in data.keys():
                                if aggregate:
                                    self._tqm._stats.update_custom_stats(k, data[k], myhost)
                                else:
                                    self._tqm._stats.set_custom_stats(k, data[k], myhost)

                    if 'add_host' in result_item:
                        # this task added a new host (add_host module)
                        new_host_info = result_item.get('add_host', dict())
                        self._add_host(new_host_info, iterator)
                        # add the info to the worker update queue so we
                        # can update the workers as we go later
                        with self._worker_update_lock:
                            self._worker_update_list.append({"add_host": new_host_info})
                    elif 'add_group' in result_item:
                        # this task added a new group (group_by module)
                        self._add_group(original_host.name, result_item)
                        # add the info to the worker update queue so we
                        # can update the workers as we go later
                        with self._worker_update_lock:
                            self._worker_update_list.append({"add_group": result_item, "host": original_host.name})

            elif host_status['status_type'] == 'failed_ignored':
                self._tqm._stats.increment('ok', host_status["host_name"])
                self._tqm._stats.increment('ignored', host_status["host_name"])
                if 'changed' in host_status['original_result'] and host_status['original_result']['changed']:
                    self._tqm._stats.increment('changed', host_status["host_name"])

            elif host_status['status_type'] in ('failed', 'failed_all'):
                self._tqm._stats.increment("failures", host_status["host_name"])
                if host_status['status_type'] == 'failed_all':
                    for h in self._inventory.get_hosts(iterator._play.hosts):
                        if h.name not in self._tqm._unreachable_hosts:
                            iterator.mark_host_failed(h)
                else:
                    iterator.mark_host_failed(original_host)
                    self._tqm._failed_hosts[host_status["host_name"]] = True

                # grab the current state and if we're iterating on the rescue portion
                # of a block then we save the failed task in a special var for use
                # within the rescue/always
                state, _ = iterator.get_next_task_for_host(original_host, peek=True)
                if iterator.is_failed(original_host) and state and state.run_state == iterator.ITERATING_COMPLETE:
                    self._tqm._failed_hosts[original_host.name] = True

                # FIXME: we don't have the original task here anymore,
                #        so we'll have to find it based on the current
                #        state in the iterator or the queue/debug cache
                if state and iterator.get_active_state(state).run_state == iterator.ITERATING_RESCUE:
                    self._tqm._stats.increment('rescued', original_host.name)
                #    self._variable_manager.set_nonpersistent_facts(
                #        original_host,
                #        dict(
                #            ansible_failed_task=original_task.serialize(),
                #            ansible_failed_result=task_result._result,
                #        ),
                #    )

            elif host_status['status_type'] == 'skipped':
                self._tqm._stats.increment("skipped", host_status["host_name"])

            elif host_status['status_type'].startswith('unreachable'):
                if host_status['status_type'] == 'unreachable':
                    iterator.mark_host_failed(self._inventory.get_host(host_status['host_name']))
                    iterator._play._removed_hosts.append(original_host.name)
                else:
                    # This used to increment 'skipped', but being inline with
                    # what ignore errors does seems to be more consistent?
                    self._tqm._stats.increment("ignored", host_status["host_name"])
                self._tqm._stats.increment("dark", host_status["host_name"])

            if host_status['role_ran']:
                # mark the role this host ran
                pass

            del self._blocked_hosts[host_status["host_name"]]
            self._pending_results -= 1
            return [host_status]
        except Queue.Empty as e:
            # FIXME: don't just pass here
            return []

    def _wait_on_handler_results(self, iterator, handler, notified_hosts):
        '''
        Wait for the handler tasks to complete, using a short sleep
        between checks to ensure we don't spin lock
        '''

        ret_results = []
        handler_results = 0

        display.debug("waiting for handler results...")
        while (self._pending_results > 0 and
               handler_results < len(notified_hosts) and
               not self._tqm._terminated):

            if self._tqm.has_dead_workers():
                raise AnsibleError("A worker was found in a dead state")

            results = self._process_pending_results(iterator)
            ret_results.extend(results)
            handler_results += len([
                r._host for r in results if r._host in notified_hosts and
                r.task_name == handler.name])
            if self._pending_results > 0:
                time.sleep(C.DEFAULT_INTERNAL_POLL_INTERVAL)

        display.debug("no more pending handlers, returning what we have")

        return ret_results

    def _wait_on_pending_results(self, iterator):
        '''
        Wait for the shared counter to drop to zero, using a short sleep
        between checks to ensure we don't spin lock
        '''

        ret_results = []

        display.debug("waiting for pending results...")
        while self._pending_results > 0 and not self._tqm._terminated:

            if self._tqm.has_dead_workers():
                raise AnsibleError("A worker was found in a dead state")

            results = self._process_pending_results(iterator)
            ret_results.extend(results)
            if self._pending_results > 0:
                time.sleep(C.DEFAULT_INTERNAL_POLL_INTERVAL)

        display.debug("no more pending results, returning what we have")

        return ret_results

    def _add_host(self, host_info, iterator=None):
        new_host = add_host(host_info, self._inventory)
        if new_host:
            self._hosts_cache_all.append(new_host.name)

    def _add_group(self, host, result_item):
        return add_group(host, result_item, self._inventory)

    def _copy_included_file(self, included_file):
        '''
        A proven safe and performant way to create a copy of an included file
        '''
        ti_copy = included_file._task.copy(exclude_parent=True)
        ti_copy._parent = included_file._task._parent

        temp_vars = ti_copy.vars.copy()
        temp_vars.update(included_file._vars)

        ti_copy.vars = temp_vars

        return ti_copy

    def _load_included_file(self, included_file, iterator, is_handler=False):
        '''
        Loads an included YAML file of tasks, applying the optional set of variables.
        '''

        display.debug("loading included file: %s" % included_file._filename)
        try:
            data = self._loader.load_from_file(included_file._filename)
            if data is None:
                return []
            elif not isinstance(data, list):
                raise AnsibleError("included task files must contain a list of tasks")

            ti_copy = self._copy_included_file(included_file)
            # pop tags out of the include args, if they were specified there, and assign
            # them to the include. If the include already had tags specified, we raise an
            # error so that users know not to specify them both ways
            tags = included_file._task.vars.pop('tags', [])
            if isinstance(tags, string_types):
                tags = tags.split(',')
            if len(tags) > 0:
                if len(included_file._task.tags) > 0:
                    raise AnsibleParserError("Include tasks should not specify tags in more than one way (both via args and directly on the task). "
                                             "Mixing tag specify styles is prohibited for whole import hierarchy, not only for single import statement",
                                             obj=included_file._task._ds)
                display.deprecated("You should not specify tags in the include parameters. All tags should be specified using the task-level option",
                                   version='2.12')
                included_file._task.tags = tags

            block_list = load_list_of_blocks(
                data,
                play=iterator._play,
                parent_block=ti_copy.build_parent_block(),
                role=included_file._task._role,
                use_handlers=is_handler,
                loader=self._loader,
                variable_manager=self._variable_manager,
            )

            # since we skip incrementing the stats when the task result is
            # first processed, we do so now for each host in the list
            for host in included_file._hosts:
                self._tqm._stats.increment('ok', host.name)

        except AnsibleError as e:
            if isinstance(e, AnsibleFileNotFound):
                reason = "Could not find or access '%s' on the Ansible Controller." % to_text(e.file_name)
            else:
                reason = to_text(e)

            # mark all of the hosts including this file as failed, send callbacks,
            # and increment the stats for this host
            for host in included_file._hosts:
                tr = TaskResult(host=host, task=included_file._task, return_data=dict(failed=True, reason=reason))
                iterator.mark_host_failed(host)
                self._tqm._failed_hosts[host.name] = True
                self._tqm._stats.increment('failures', host.name)
                self._tqm.send_callback('v2_runner_on_failed', tr)
            return []

        # finally, send the callback and return the list of blocks loaded
        self._tqm.send_callback('v2_playbook_on_include', included_file)
        display.debug("done processing included file")
        return block_list

    def run_handlers(self, iterator, play_context):
        '''
        Runs handlers on those hosts which have been notified.
        '''

        result = self._tqm.RUN_OK

        for handler_block in iterator._play.handlers:
            # FIXME: handlers need to support the rescue/always portions of blocks too,
            #        but this may take some work in the iterator and gets tricky when
            #        we consider the ability of meta tasks to flush handlers
            for handler in handler_block.block:
                if handler.notified_hosts:
                    result = self._do_handler_run(handler, handler.get_name(), iterator=iterator, play_context=play_context)
                    if not result:
                        break
        return result

    def _do_handler_run(self, handler, handler_name, iterator, play_context, notified_hosts=None):

        # FIXME: need to use iterator.get_failed_hosts() instead?
        # if not len(self.get_hosts_remaining(iterator._play)):
        #     self._tqm.send_callback('v2_playbook_on_no_hosts_remaining')
        #     result = False
        #     break
        if notified_hosts is None:
            notified_hosts = handler.notified_hosts[:]

        notified_hosts = self._filter_notified_hosts(notified_hosts)

        if len(notified_hosts) > 0:
            saved_name = handler.name
            handler.name = handler_name
            self._tqm.send_callback('v2_playbook_on_handler_task_start', handler)
            handler.name = saved_name

        bypass_host_loop = False
        try:
            action = plugin_loader.action_loader.get(handler.action, class_only=True)
            if getattr(action, 'BYPASS_HOST_LOOP', False):
                bypass_host_loop = True
        except KeyError:
            # we don't care here, because the action may simply not have a
            # corresponding action plugin
            pass

        host_results = []
        for host in notified_hosts:
            if not iterator.is_failed(host) or iterator._play.force_handlers:
                task_vars = self._variable_manager.get_vars(play=iterator._play, host=host, task=handler,
                                                            _hosts=self._hosts_cache, _hosts_all=self._hosts_cache_all)
                self.add_tqm_variables(task_vars, play=iterator._play)
                templar = Templar(loader=self._loader, variables=task_vars)
                if not handler.cached_name:
                    handler.name = templar.template(handler.name)
                    handler.cached_name = True

                self._queue_task(host, handler, task_vars, play_context)

                if templar.template(handler.run_once) or bypass_host_loop:
                    break

        # collect the results from the handler run
        host_results = self._wait_on_handler_results(iterator, handler, notified_hosts)

        included_files = IncludedFile.process_include_results(
            host_results,
            iterator=iterator,
            loader=self._loader,
            variable_manager=self._variable_manager
        )

        result = True
        if len(included_files) > 0:
            for included_file in included_files:
                try:
                    new_blocks = self._load_included_file(included_file, iterator=iterator, is_handler=True)
                    # for every task in each block brought in by the include, add the list
                    # of hosts which included the file to the notified_handlers dict
                    for block in new_blocks:
                        iterator._play.handlers.append(block)
                        for task in block.block:
                            task_name = task.get_name()
                            display.debug("adding task '%s' included in handler '%s'" % (task_name, handler_name))
                            task.notified_hosts = included_file._hosts[:]
                            result = self._do_handler_run(
                                handler=task,
                                handler_name=task_name,
                                iterator=iterator,
                                play_context=play_context,
                                notified_hosts=included_file._hosts[:],
                            )
                            if not result:
                                break
                except AnsibleError as e:
                    for host in included_file._hosts:
                        iterator.mark_host_failed(host)
                        self._tqm._failed_hosts[host.name] = True
                    display.warning(to_text(e))
                    continue

        # remove hosts from notification list
        handler.notified_hosts = [
            h for h in handler.notified_hosts
            if h not in notified_hosts]
        display.debug("done running handlers, result is: %s" % result)
        return result

    def _filter_notified_hosts(self, notified_hosts):
        '''
        Filter notified hosts accordingly to strategy
        '''

        # As main strategy is linear, we do not filter hosts
        # We return a copy to avoid race conditions
        return notified_hosts[:]

    def _take_step(self, task, host=None):

        ret = False
        msg = u'Perform task: %s ' % task
        if host:
            msg += u'on %s ' % host
        msg += u'(N)o/(y)es/(c)ontinue: '
        resp = display.prompt(msg)

        if resp.lower() in ['y', 'yes']:
            display.debug("User ran task")
            ret = True
        elif resp.lower() in ['c', 'continue']:
            display.debug("User ran task and canceled step mode")
            self._step = False
            ret = True
        else:
            display.debug("User skipped task")

        display.banner(msg)

        return ret

    def _cond_not_supported_warn(self, task_name):
        display.warning("%s task does not support when conditional" % task_name)

    def _execute_meta(self, task, play_context, iterator, target_host):

        # meta tasks store their args in the _raw_params field of args,
        # since they do not use k=v pairs, so get that
        meta_action = task.args.get('_raw_params')

        def _evaluate_conditional(h):
            all_vars = self._variable_manager.get_vars(play=iterator._play, host=h, task=task,
                                                       _hosts=self._hosts_cache, _hosts_all=self._hosts_cache_all)
            templar = Templar(loader=self._loader, variables=all_vars)
            return evaluate_conditional(task.when, task.get_ds(), templar, all_vars)

        skipped = False
        msg = ''
        if meta_action == 'noop':
            # FIXME: issue a callback for the noop here?
            if task.when:
                self._cond_not_supported_warn(meta_action)
            msg = "noop"
        elif meta_action == 'flush_handlers':
            if task.when:
                self._cond_not_supported_warn(meta_action)
            self._flushed_hosts[target_host] = True
            self.run_handlers(iterator, play_context)
            self._flushed_hosts[target_host] = False
            msg = "ran handlers"
        elif meta_action == 'refresh_inventory' or self.flush_cache:
            if task.when:
                self._cond_not_supported_warn(meta_action)
            self._inventory.refresh_inventory()
            self._set_hosts_cache(iterator._play)
            msg = "inventory successfully refreshed"
        elif meta_action == 'clear_facts':
            if _evaluate_conditional(target_host):
                for host in self._inventory.get_hosts(iterator._play.hosts):
                    hostname = host.get_name()
                    self._variable_manager.clear_facts(hostname)
                msg = "facts cleared"
            else:
                skipped = True
        elif meta_action == 'clear_host_errors':
            if _evaluate_conditional(target_host):
                for host in self._inventory.get_hosts(iterator._play.hosts):
                    self._tqm._failed_hosts.pop(host.name, False)
                    self._tqm._unreachable_hosts.pop(host.name, False)
                    iterator._host_states[host.name].fail_state = iterator.FAILED_NONE
                msg = "cleared host errors"
            else:
                skipped = True
        elif meta_action == 'end_play':
            if _evaluate_conditional(target_host):
                for host in self._inventory.get_hosts(iterator._play.hosts):
                    if host.name not in self._tqm._unreachable_hosts:
                        iterator._host_states[host.name].run_state = iterator.ITERATING_COMPLETE
                msg = "ending play"
        elif meta_action == 'end_host':
            if _evaluate_conditional(target_host):
                iterator._host_states[target_host.name].run_state = iterator.ITERATING_COMPLETE
                msg = "ending play for %s" % target_host.name
            else:
                skipped = True
                msg = "end_host conditional evaluated to false, continuing execution for %s" % target_host.name
        elif meta_action == 'reset_connection':
            all_vars = self._variable_manager.get_vars(
                play=iterator._play,
                host=target_host,
                task=task,
                _hosts=self._hosts_cache,
                _hosts_all=self._hosts_cache_all,
            )
            templar = Templar(loader=self._loader, variables=all_vars)

            # apply the given task's information to the connection info,
            # which may override some fields already set by the play or
            # the options specified on the command line
            # FIXME: hacky... there may be a better way
            play_context.deserialize(
                set_task_and_variable_override(
                    play_context=self._play_context.serialize(),
                    task=task.serialize(),
                    variables=all_vars,
                    templar=templar,
                )
            )

            # fields set from the play/task may be based on variables, so we have to
            # do the same kind of post validation step on it here before we use it.
            post_validate(play_context, templar=templar)

            # now that the play context is finalized, if the remote_addr is not set
            # default to using the host's address field as the remote address
            if not play_context.remote_addr:
                play_context.remote_addr = target_host.address

            # We also add "magic" variables back into the variables dict to make sure
            # a certain subset of variables exist.
            play_context.update_vars(all_vars)

            if task.when:
                self._cond_not_supported_warn(meta_action)

            if target_host in self._active_connections:
                connection = Connection(self._active_connections[target_host])
                del self._active_connections[target_host]
            else:
                connection = plugin_loader.connection_loader.get(play_context.connection, play_context, os.devnull)
                play_context.set_attributes_from_plugin(connection)

            if connection:
                try:
                    connection.reset()
                    msg = 'reset connection'
                except ConnectionError as e:
                    # most likely socket is already closed
                    display.debug("got an error while closing persistent connection: %s" % e)
            else:
                msg = 'no connection, nothing to reset'
        else:
            raise AnsibleError("invalid meta action requested: %s" % meta_action, obj=task._ds)

        result = {'msg': msg}
        if skipped:
            result['skipped'] = True
        else:
            result['changed'] = False

        display.vv("META: %s" % msg)

        # FIXME: don't hardcode fields
        return [{
            'host_name': target_host.name,
            'task_uuid': task._uuid,
            'status_type': "ok",
            'status_msg': "ran meta ok",
            'original_result': result,
            'changed': False,
            'role_ran': False,
        }]

    def get_hosts_left(self, iterator):
        ''' returns list of available hosts for this iterator by filtering out unreachables '''

        hosts_left = []
        for host in self._hosts_cache:
            if host not in self._tqm._unreachable_hosts:
                try:
                    hosts_left.append(self._inventory.hosts[host])
                except KeyError:
                    hosts_left.append(self._inventory.get_host(host))
        return hosts_left

    def update_active_connections(self, results):
        ''' updates the current active persistent connections '''
        for r in results:
            # FIXME: not sure why we need to check and see if task fields is here now...
            if '_task_fields' in r and 'args' in r['_task_fields']:
                socket_path = r['_task_fields']['args'].get('_ansible_socket')
                if socket_path:
                    if r._host not in self._active_connections:
                        self._active_connections[r._host] = socket_path


class NextAction(object):
    """ The next action after an interpreter's exit. """
    REDO = 1
    CONTINUE = 2
    EXIT = 3

    def __init__(self, result=EXIT):
        self.result = result


class Debugger(cmd.Cmd):
    prompt_continuous = '> '  # multiple lines

    def __init__(self, task, host, task_vars, play_context, result, next_action):
        # cmd.Cmd is old-style class
        cmd.Cmd.__init__(self)

        self.prompt = '[%s] %s (debug)> ' % (host, task)
        self.intro = None
        self.scope = {}
        self.scope['task'] = task
        self.scope['task_vars'] = task_vars
        self.scope['host'] = host
        self.scope['play_context'] = play_context
        self.scope['result'] = result
        self.next_action = next_action

    def cmdloop(self):
        try:
            cmd.Cmd.cmdloop(self)
        except KeyboardInterrupt:
            pass

    do_h = cmd.Cmd.do_help

    def do_EOF(self, args):
        """Quit"""
        return self.do_quit(args)

    def do_quit(self, args):
        """Quit"""
        display.display('User interrupted execution')
        self.next_action.result = NextAction.EXIT
        return True

    do_q = do_quit

    def do_continue(self, args):
        """Continue to next result"""
        self.next_action.result = NextAction.CONTINUE
        return True

    do_c = do_continue

    def do_redo(self, args):
        """Schedule task for re-execution. The re-execution may not be the next result"""
        self.next_action.result = NextAction.REDO
        return True

    do_r = do_redo

    def do_update_task(self, args):
        """Recreate the task from ``task._ds``, and template with updated ``task_vars``"""
        templar = Templar(None, shared_loader_obj=None, variables=self.scope['task_vars'])
        task = self.scope['task']
        task = task.load_data(task._ds)
        self.scope['task'] = post_validate(task.serialize(), templar)

    do_u = do_update_task

    def evaluate(self, args):
        try:
            return eval(args, globals(), self.scope)
        except Exception:
            t, v = sys.exc_info()[:2]
            if isinstance(t, str):
                exc_type_name = t
            else:
                exc_type_name = t.__name__
            display.display('***%s:%s' % (exc_type_name, repr(v)))
            raise

    def do_pprint(self, args):
        """Pretty Print"""
        try:
            result = self.evaluate(args)
            display.display(pprint.pformat(result))
        except Exception:
            pass

    do_p = do_pprint

    def execute(self, args):
        try:
            code = compile(args + '\n', '<stdin>', 'single')
            exec(code, globals(), self.scope)
        except Exception:
            t, v = sys.exc_info()[:2]
            if isinstance(t, str):
                exc_type_name = t
            else:
                exc_type_name = t.__name__
            display.display('***%s:%s' % (exc_type_name, repr(v)))
            raise

    def default(self, line):
        try:
            self.execute(line)
        except Exception:
            pass
