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

import contextlib
import fcntl
import os
import sys
import termios
import traceback
from multiprocessing.queues import Queue

from ansible import context
from ansible.errors import AnsibleConnectionFailure, AnsibleError
from ansible.executor.task_executor import TaskExecutor
from ansible.module_utils.common.collections import is_sequence
from ansible.module_utils.common.text.converters import to_text
from ansible.plugins.loader import init_plugin_loader
from ansible.utils.display import Display
from ansible.utils.multiprocessing import context as multiprocessing_context

from jinja2.exceptions import TemplateNotFound

__all__ = ['WorkerProcess']

display = Display()

current_worker = None


class WorkerQueue(Queue):
    """Queue that raises AnsibleError items on get()."""
    def get(self, *args, **kwargs):
        result = super(WorkerQueue, self).get(*args, **kwargs)
        if isinstance(result, AnsibleError):
            raise result
        return result


class WorkerProcess(multiprocessing_context.Process):  # type: ignore[name-defined]
    '''
    The worker thread class, which uses TaskExecutor to run tasks
    read from a job queue and pushes results into a results queue
    for reading later.
    '''

    def __init__(self, final_q, task_vars, host, task, play_context, loader, variable_manager, shared_loader_obj, worker_id, cliargs):

        super(WorkerProcess, self).__init__()
        # takes a task queue manager as the sole param:
        self._final_q = final_q
        self._task_vars = task_vars
        self._host = host
        self._task = task
        self._play_context = play_context
        self._loader = loader
        self._variable_manager = variable_manager
        self._shared_loader_obj = shared_loader_obj

        # NOTE: this works due to fork, if switching to threads this should change to per thread storage of temp files
        # clear var to ensure we only delete files for this child
        self._loader._tempfiles = set()

        self.worker_queue = WorkerQueue(ctx=multiprocessing_context)
        self.worker_id = worker_id

        self._cliargs = cliargs

        self._detached = False
        self._detach_error = None
        self._master = None
        self._slave = None

    def start(self):
        '''
        multiprocessing.Process replaces the worker's stdin with a new file
        but we wish to preserve it if it is connected to a terminal.
        Therefore dup a copy prior to calling the real start(),
        ensuring the descriptor is preserved somewhere in the new child, and
        make sure it is closed in the parent when start() completes.
        '''

        # FUTURE: this lock can be removed once a more generalized pre-fork thread pause is in place
        if multiprocessing_context.get_start_method() == 'fork':
            self._master, self._slave = os.openpty()
            cm = contextlib.ExitStack()
            cm.callback(os.close, self._slave)
        else:
            cm = contextlib.nullcontext()
        with display._lock, cm:
            super(WorkerProcess, self).start()

    def close(self):
        if self._master:
            os.close(self._master)
        super().close()

    def _hard_exit(self, e):
        '''
        There is no safe exception to return to higher level code that does not
        risk an innocent try/except finding itself executing in the wrong
        process. All code executing above WorkerProcess.run() on the stack
        conceptually belongs to another program.
        '''

        try:
            display.debug(u"WORKER HARD EXIT: %s" % to_text(e))
        except BaseException:
            # If the cause of the fault is IOError being generated by stdio,
            # attempting to log a debug message may trigger another IOError.
            # Try printing once then give up.
            pass

        os._exit(1)

    @contextlib.contextmanager
    def _detach(self):
        '''
        The intent here is to detach the child process from the inherited stdio fds,
        including /dev/tty. Children should use Display, instead of direct interactions
        with stdio fds.
        '''
        try:
            if multiprocessing_context.get_start_method() != 'fork':
                # If we aren't forking, we don't have inherited pty
                _io = open(os.devnull, 'w')
            else:
                os.close(self._master)
                os.setsid()
                fcntl.ioctl(self._slave, termios.TIOCSCTTY)
                _io = os.fdopen(self._slave, 'w')
            sys.stdin = sys.__stdin__ = _io  # type: ignore[misc]
            sys.stdout = sys.__stdout__ = sys.stdin  # type: ignore[misc]
            sys.stderr = sys.__stderr__ = sys.stdin  # type: ignore[misc]
        except Exception as e:
            # We aren't in a place we can reliably notify from, just pass here, evaluate self._detached later
            self._detach_error = (e, traceback.format_exc())
        else:
            self._detached = True

        yield

        if self._slave:
            os.close(self._slave)

    def run(self):
        '''
        Wrap _run() to ensure no possibility an errant exception can cause
        control to return to the StrategyBase task loop, or any other code
        higher in the stack.

        As multiprocessing in Python 2.x provides no protection, it is possible
        a try/except added in far-away code can cause a crashed child process
        to suddenly assume the role and prior state of its parent.
        '''
        try:
            display.set_queue(self._final_q)
            with self._detach():
                return self._run()
        except BaseException:
            self._hard_exit(traceback.format_exc())

    def _run(self):
        '''
        Called when the process is started.  Pushes the result onto the
        results queue. We also remove the host from the blocked hosts list, to
        signify that they are ready for their next task.
        '''

        # import cProfile, pstats, StringIO
        # pr = cProfile.Profile()
        # pr.enable()

        # Set the queue on Display so calls to Display.display are proxied over the queue
        display.set_queue(self._final_q)

        if not self._detached:
            display.debug(f'Could not detach from stdio: {self._detach_error[1]}')
            display.error(f'Could not detach from stdio: {self._detach_error[0]}')
            os._exit(1)

        global current_worker
        current_worker = self

        if multiprocessing_context.get_start_method() != 'fork':
            context.CLIARGS = self._cliargs
            # Initialize plugin loader after parse, so that the init code can utilize parsed arguments
            cli_collections_path = context.CLIARGS.get('collections_path') or []
            if not is_sequence(cli_collections_path):
                # In some contexts ``collections_path`` is singular
                cli_collections_path = [cli_collections_path]
            init_plugin_loader(cli_collections_path)

        try:
            # execute the task and build a TaskResult from the result
            display.debug("running TaskExecutor() for %s/%s" % (self._host, self._task))
            executor_result = TaskExecutor(
                self._host,
                self._task,
                self._task_vars,
                self._play_context,
                self._loader,
                self._shared_loader_obj,
                self._final_q,
                self._variable_manager,
            ).run()

            display.debug("done running TaskExecutor() for %s/%s [%s]" % (self._host, self._task, self._task._uuid))
            self._host.vars = dict()
            self._host.groups = []

            # put the result on the result queue
            display.debug("sending task result for task %s" % self._task._uuid)
            try:
                self._final_q.send_task_result(
                    self._host.name,
                    self._task._uuid,
                    executor_result,
                    task_fields=self._task.dump_attrs(),
                )
            except Exception as e:
                display.debug(f'failed to send task result ({e}), sending surrogate result')
                self._final_q.send_task_result(
                    self._host.name,
                    self._task._uuid,
                    # Overriding the task result, to represent the failure
                    {
                        'failed': True,
                        'msg': f'{e}',
                        'exception': traceback.format_exc(),
                    },
                    # The failure pickling may have been caused by the task attrs, omit for safety
                    {},
                )
            display.debug("done sending task result for task %s" % self._task._uuid)

        except AnsibleConnectionFailure:
            self._host.vars = dict()
            self._host.groups = []
            self._final_q.send_task_result(
                self._host.name,
                self._task._uuid,
                dict(unreachable=True),
                task_fields=self._task.dump_attrs(),
            )

        except Exception as e:
            if not isinstance(e, (IOError, EOFError, KeyboardInterrupt, SystemExit)) or isinstance(e, TemplateNotFound):
                try:
                    self._host.vars = dict()
                    self._host.groups = []
                    self._final_q.send_task_result(
                        self._host.name,
                        self._task._uuid,
                        dict(failed=True, exception=to_text(traceback.format_exc()), stdout=''),
                        task_fields=self._task.dump_attrs(),
                    )
                except Exception:
                    display.debug(u"WORKER EXCEPTION: %s" % to_text(e))
                    display.debug(u"WORKER TRACEBACK: %s" % to_text(traceback.format_exc()))
                finally:
                    self._clean_up()

        display.debug("WORKER PROCESS EXITING")

        # pr.disable()
        # s = StringIO.StringIO()
        # sortby = 'time'
        # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        # ps.print_stats()
        # with open('worker_%06d.stats' % os.getpid(), 'w') as f:
        #     f.write(s.getvalue())

    def _clean_up(self):
        # NOTE: see note in init about forks
        # ensure we cleanup all temp files for this worker
        self._loader.cleanup_all_tmp_files()
