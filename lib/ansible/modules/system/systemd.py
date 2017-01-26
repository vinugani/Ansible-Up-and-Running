#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2016, Brian Coca <bcoca@ansible.com>
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

ANSIBLE_METADATA = {'status': ['stableinterface'],
                    'supported_by': 'core',
                    'version': '1.0'}

DOCUMENTATION = '''
module: systemd
author:
    - "Ansible Core Team"
version_added: "2.2"
short_description:  Manage services.
description:
    - Controls systemd services on remote hosts.
options:
    name:
        required: true
        description:
            - Name of the service.
        aliases: ['unit', 'service']
    state:
        required: false
        default: null
        choices: [ 'started', 'stopped', 'restarted', 'reloaded' ]
        description:
            - C(started)/C(stopped) are idempotent actions that will not run commands unless necessary.
              C(restarted) will always bounce the service. C(reloaded) will always reload.
    enabled:
        required: false
        choices: [ "yes", "no" ]
        default: null
        description:
            - Whether the service should start on boot. B(At least one of state and enabled are required.)
    masked:
        required: false
        choices: [ "yes", "no" ]
        default: null
        description:
            - Whether the unit should be masked or not, a masked unit is impossible to start.
    daemon_reload:
        required: false
        default: no
        choices: [ "yes", "no" ]
        description:
            - run daemon-reload before doing any other operations, to make sure systemd has read any changes.
        aliases: ['daemon-reload']
    user:
        required: false
        default: no
        choices: [ "yes", "no" ]
        description:
            - run systemctl talking to the service manager of the calling user, rather than the service manager
              of the system.
    no_block:
        required: false
        default: no
        choices: [ "yes", "no" ]
        description:
            - Do not synchronously wait for the requested operation to finish.
              Enqueued job will continue without Ansible blocking on its completion.
        version_added: "2.3"
notes:
    - One option other than name is required.
requirements:
    - A system managed by systemd
'''

EXAMPLES = '''
# Example action to start service httpd, if not running
- systemd: state=started name=httpd

# Example action to stop service cron on debian, if running
- systemd: name=cron state=stopped

# Example action to restart service cron on centos, in all cases, also issue daemon-reload to pick up config changes
- systemd:
    state: restarted
    daemon_reload: yes
    name: crond

# Example action to reload service httpd, in all cases
- systemd:
    name: httpd
    state: reloaded

# Example action to enable service httpd and ensure it is not masked
- systemd:
    name: httpd
    enabled: yes
    masked: no

# Example action to enable a timer for dnf-automatic
- systemd:
    name: dnf-automatic.timer
    state: started
    enabled: True
'''

RETURN = '''
status:
    description: A dictionary with the key=value pairs returned from `systemctl show`
    returned: success
    type: complex
    sample: {
            "ActiveEnterTimestamp": "Sun 2016-05-15 18:28:49 EDT",
            "ActiveEnterTimestampMonotonic": "8135942",
            "ActiveExitTimestampMonotonic": "0",
            "ActiveState": "active",
            "After": "auditd.service systemd-user-sessions.service time-sync.target systemd-journald.socket basic.target system.slice",
            "AllowIsolate": "no",
            "Before": "shutdown.target multi-user.target",
            "BlockIOAccounting": "no",
            "BlockIOWeight": "1000",
            "CPUAccounting": "no",
            "CPUSchedulingPolicy": "0",
            "CPUSchedulingPriority": "0",
            "CPUSchedulingResetOnFork": "no",
            "CPUShares": "1024",
            "CanIsolate": "no",
            "CanReload": "yes",
            "CanStart": "yes",
            "CanStop": "yes",
            "CapabilityBoundingSet": "18446744073709551615",
            "ConditionResult": "yes",
            "ConditionTimestamp": "Sun 2016-05-15 18:28:49 EDT",
            "ConditionTimestampMonotonic": "7902742",
            "Conflicts": "shutdown.target",
            "ControlGroup": "/system.slice/crond.service",
            "ControlPID": "0",
            "DefaultDependencies": "yes",
            "Delegate": "no",
            "Description": "Command Scheduler",
            "DevicePolicy": "auto",
            "EnvironmentFile": "/etc/sysconfig/crond (ignore_errors=no)",
            "ExecMainCode": "0",
            "ExecMainExitTimestampMonotonic": "0",
            "ExecMainPID": "595",
            "ExecMainStartTimestamp": "Sun 2016-05-15 18:28:49 EDT",
            "ExecMainStartTimestampMonotonic": "8134990",
            "ExecMainStatus": "0",
            "ExecReload": "{ path=/bin/kill ; argv[]=/bin/kill -HUP $MAINPID ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }",
            "ExecStart": "{ path=/usr/sbin/crond ; argv[]=/usr/sbin/crond -n $CRONDARGS ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }",
            "FragmentPath": "/usr/lib/systemd/system/crond.service",
            "GuessMainPID": "yes",
            "IOScheduling": "0",
            "Id": "crond.service",
            "IgnoreOnIsolate": "no",
            "IgnoreOnSnapshot": "no",
            "IgnoreSIGPIPE": "yes",
            "InactiveEnterTimestampMonotonic": "0",
            "InactiveExitTimestamp": "Sun 2016-05-15 18:28:49 EDT",
            "InactiveExitTimestampMonotonic": "8135942",
            "JobTimeoutUSec": "0",
            "KillMode": "process",
            "KillSignal": "15",
            "LimitAS": "18446744073709551615",
            "LimitCORE": "18446744073709551615",
            "LimitCPU": "18446744073709551615",
            "LimitDATA": "18446744073709551615",
            "LimitFSIZE": "18446744073709551615",
            "LimitLOCKS": "18446744073709551615",
            "LimitMEMLOCK": "65536",
            "LimitMSGQUEUE": "819200",
            "LimitNICE": "0",
            "LimitNOFILE": "4096",
            "LimitNPROC": "3902",
            "LimitRSS": "18446744073709551615",
            "LimitRTPRIO": "0",
            "LimitRTTIME": "18446744073709551615",
            "LimitSIGPENDING": "3902",
            "LimitSTACK": "18446744073709551615",
            "LoadState": "loaded",
            "MainPID": "595",
            "MemoryAccounting": "no",
            "MemoryLimit": "18446744073709551615",
            "MountFlags": "0",
            "Names": "crond.service",
            "NeedDaemonReload": "no",
            "Nice": "0",
            "NoNewPrivileges": "no",
            "NonBlocking": "no",
            "NotifyAccess": "none",
            "OOMScoreAdjust": "0",
            "OnFailureIsolate": "no",
            "PermissionsStartOnly": "no",
            "PrivateNetwork": "no",
            "PrivateTmp": "no",
            "RefuseManualStart": "no",
            "RefuseManualStop": "no",
            "RemainAfterExit": "no",
            "Requires": "basic.target",
            "Restart": "no",
            "RestartUSec": "100ms",
            "Result": "success",
            "RootDirectoryStartOnly": "no",
            "SameProcessGroup": "no",
            "SecureBits": "0",
            "SendSIGHUP": "no",
            "SendSIGKILL": "yes",
            "Slice": "system.slice",
            "StandardError": "inherit",
            "StandardInput": "null",
            "StandardOutput": "journal",
            "StartLimitAction": "none",
            "StartLimitBurst": "5",
            "StartLimitInterval": "10000000",
            "StatusErrno": "0",
            "StopWhenUnneeded": "no",
            "SubState": "running",
            "SyslogLevelPrefix": "yes",
            "SyslogPriority": "30",
            "TTYReset": "no",
            "TTYVHangup": "no",
            "TTYVTDisallocate": "no",
            "TimeoutStartUSec": "1min 30s",
            "TimeoutStopUSec": "1min 30s",
            "TimerSlackNSec": "50000",
            "Transient": "no",
            "Type": "simple",
            "UMask": "0022",
            "UnitFileState": "enabled",
            "WantedBy": "multi-user.target",
            "Wants": "system.slice",
            "WatchdogTimestampMonotonic": "0",
            "WatchdogUSec": "0",
        }
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.service import sysv_exists, sysv_is_enabled, fail_if_missing
from ansible.module_utils._text import to_native


def is_running_service(service_status):
    return service_status['ActiveState'] in set(['active', 'activating'])


# ===========================================
# Main control flow

def main():
    # initialize
    module = AnsibleModule(
        argument_spec = dict(
                name = dict(required=True, type='str', aliases=['unit', 'service']),
                state = dict(choices=[ 'started', 'stopped', 'restarted', 'reloaded'], type='str'),
                enabled = dict(type='bool'),
                masked = dict(type='bool'),
                daemon_reload = dict(type='bool', default=False, aliases=['daemon-reload']),
                user = dict(type='bool', default=False),
                no_block = dict(type='bool', default=False),
            ),
            supports_check_mode=True,
            required_one_of=[['state', 'enabled', 'masked', 'daemon_reload']],
        )

    systemctl = module.get_bin_path('systemctl')
    if module.params['user']:
        systemctl = systemctl + " --user"
    if module.params['no_block']:
        systemctl = systemctl + " --no-block"
    unit = module.params['name']
    rc = 0
    out = err = ''
    result = {
        'name':  unit,
        'changed': False,
        'status': {},
        'warnings': [],
    }

    # Run daemon-reload first, if requested
    if module.params['daemon_reload']:
        (rc, out, err) = module.run_command("%s daemon-reload" % (systemctl))
        if rc != 0:
            module.fail_json(msg='failure %d during daemon-reload: %s' % (rc, err))

    found = False
    is_initd = sysv_exists(unit)
    is_systemd = False

    # check service data, cannot error out on rc as it changes across versions, assume not found
    (rc, out, err) = module.run_command("%s show '%s'" % (systemctl, unit))
    if rc == 0:
        # load return of systemctl show into dictionary for easy access and return
        multival = []
        if out:
            k = None
            for line in to_native(out).split('\n'): # systemd can have multiline values delimited with {}
                if line.strip():
                    if k is None:
                        if '=' in line:
                            k,v = line.split('=', 1)
                            if v.lstrip().startswith('{'):
                                if not v.rstrip().endswith('}'):
                                    multival.append(line)
                                    continue
                            result['status'][k] = v.strip()
                            k = None
                    else:
                        if line.rstrip().endswith('}'):
                            result['status'][k] = '\n'.join(multival).strip()
                            multival = []
                            k = None
                        else:
                            multival.append(line)

            is_systemd = 'LoadState' in result['status'] and result['status']['LoadState'] != 'not-found'

            # Check for loading error
            if is_systemd and 'LoadError' in result['status']:
                module.fail_json(msg="Error loading unit file '%s': %s" % (unit, result['status']['LoadError']))

    # Does service exist?
    found = is_systemd or is_initd
    if is_initd and not is_systemd:
        result['warnings'].append('The service (%s) is actually an init script but the system is managed by systemd' % unit)

    # mask/unmask the service, if requested, can operate on services before they are installed
    if module.params['masked'] is not None:
        # state is not masked unless systemd affirms otherwise
        masked = ('LoadState' in result['status'] and result['status']['LoadState'] == 'masked')

        if masked != module.params['masked']:
            result['changed'] = True
            if module.params['masked']:
                action = 'mask'
            else:
                action = 'unmask'

            if not module.check_mode:
                (rc, out, err) = module.run_command("%s %s '%s'" % (systemctl, action, unit))
                if rc != 0:
                    # some versions of system CAN mask/unmask non existing services, we only fail on missing if they don't
                    fail_if_missing(module, found, unit, msg='host')


    # Enable/disable service startup at boot if requested
    if module.params['enabled'] is not None:

        if module.params['enabled']:
            action = 'enable'
        else:
            action = 'disable'

        fail_if_missing(module, found, unit, msg='host')

        # do we need to enable the service?
        enabled = False
        (rc, out, err) = module.run_command("%s is-enabled '%s'" % (systemctl, unit))

        # check systemctl result or if it is a init script
        if rc == 0:
            enabled = True
        elif rc == 1:
            # if not a user service and both init script and unit file exist stdout should have enabled/disabled, otherwise use rc entries
            if not module.params['user'] and \
               is_initd and \
               (not out.strip().endswith('disabled') or sysv_is_enabled(unit)):

                enabled = True

        # default to current state
        result['enabled'] = enabled

        # Change enable/disable if needed
        if enabled != module.params['enabled']:
            result['changed'] = True
            if not module.check_mode:
                (rc, out, err) = module.run_command("%s %s '%s'" % (systemctl, action, unit))
                if rc != 0:
                    module.fail_json(msg="Unable to %s service %s: %s" % (action, unit, out + err))

            result['enabled'] = not enabled

    # set service state if requested
    if module.params['state'] is not None:
        fail_if_missing(module, found, unit, msg="host")

        # default to desired state
        result['state'] = module.params['state']

        # What is current service state?
        if 'ActiveState' in result['status']:
            action = None
            if module.params['state'] == 'started':
                if not is_running_service(result['status']):
                    action = 'start'
            elif module.params['state'] == 'stopped':
                if is_running_service(result['status']):
                    action = 'stop'
            else:
                if not is_running_service(result['status']):
                    action = 'start'
                else:
                    action = module.params['state'][:-2] # remove 'ed' from restarted/reloaded
                result['state'] = 'started'

            if action:
                result['changed'] = True
                if not module.check_mode:
                    (rc, out, err) = module.run_command("%s %s '%s'" % (systemctl, action, unit))
                    if rc != 0:
                        module.fail_json(msg="Unable to %s service %s: %s" % (action, unit, err))
        else:
            # this should not happen?
            module.fail_json(msg="Service is in unknown state", status=result['status'])


    module.exit_json(**result)

if __name__ == '__main__':
    main()
