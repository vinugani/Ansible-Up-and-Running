"""Delegate test execution to another environment."""
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os
import re
import sys
import tempfile

from . import types as t

from .io import (
    make_dirs,
    read_text_file,
)

from .executor import (
    create_shell_command,
    run_pypi_proxy,
    get_python_interpreter,
    get_python_version,
)

from .config import (
    TestConfig,
    EnvironmentConfig,
    IntegrationConfig,
    WindowsIntegrationConfig,
    NetworkIntegrationConfig,
    ShellConfig,
    SanityConfig,
    UnitsConfig,
)

from .core_ci import (
    AnsibleCoreCI,
    SshKey,
)

from .manage_ci import (
    ManagePosixCI,
    ManageWindowsCI,
    get_ssh_key_setup,
)

from .util import (
    ApplicationError,
    common_environment,
    display,
    ANSIBLE_BIN_PATH,
    ANSIBLE_TEST_DATA_ROOT,
    ANSIBLE_LIB_ROOT,
    ANSIBLE_TEST_ROOT,
    tempdir,
    SUPPORTED_PYTHON_VERSIONS,
)

from .util_common import (
    run_command,
    ResultType,
    create_interpreter_wrapper,
    get_docker_completion,
    get_remote_completion,
)

from .docker_util import (
    docker_exec,
    docker_get,
    docker_inspect,
    docker_pull,
    docker_put,
    docker_rm,
    docker_run,
    docker_network_disconnect,
    get_docker_command,
    get_docker_hostname,
)

from .containers import (
    SshConnectionDetail,
    support_container_context,
)

from .data import (
    data_context,
)

from .payload import (
    create_payload,
)

from .venv import (
    create_virtual_environment,
)

from .ci import (
    get_ci_provider,
)


def check_delegation_args(args):
    """
    :type args: CommonConfig
    """
    if not isinstance(args, EnvironmentConfig):
        return

    if args.docker:
        get_python_version(args, get_docker_completion(), args.docker_raw)
    elif args.remote:
        get_python_version(args, get_remote_completion(), args.remote)


def delegate(args, exclude, require):
    """
    :type args: EnvironmentConfig
    :type exclude: list[str]
    :type require: list[str]
    :rtype: bool
    """
    if isinstance(args, TestConfig):
        args.metadata.ci_provider = get_ci_provider().code

        make_dirs(ResultType.TMP.path)

        with tempfile.NamedTemporaryFile(prefix='metadata-', suffix='.json', dir=ResultType.TMP.path) as metadata_fd:
            args.metadata_path = os.path.join(ResultType.TMP.relative_path, os.path.basename(metadata_fd.name))
            args.metadata.to_file(args.metadata_path)

            try:
                return delegate_command(args, exclude, require)
            finally:
                args.metadata_path = None
    else:
        return delegate_command(args, exclude, require)


def delegate_command(args, exclude, require):
    """
    :type args: EnvironmentConfig
    :type exclude: list[str]
    :type require: list[str]
    :rtype: bool
    """
    if args.venv:
        delegate_venv(args, exclude, require)
        return True

    if args.docker:
        delegate_docker(args, exclude, require)
        return True

    if args.remote:
        delegate_remote(args, exclude, require)
        return True

    return False


def delegate_venv(args,  # type: EnvironmentConfig
                  exclude,  # type: t.List[str]
                  require,  # type: t.List[str]
                  ):  # type: (...) -> None
    """Delegate ansible-test execution to a virtual environment using venv or virtualenv."""
    if args.python:
        versions = (args.python_version,)
    else:
        versions = SUPPORTED_PYTHON_VERSIONS

    if args.venv_system_site_packages:
        suffix = '-ssp'
    else:
        suffix = ''

    venvs = dict((version, os.path.join(ResultType.TMP.path, 'delegation', 'python%s%s' % (version, suffix))) for version in versions)
    venvs = dict((version, path) for version, path in venvs.items() if create_virtual_environment(args, version, path, args.venv_system_site_packages))

    if not venvs:
        raise ApplicationError('No usable virtual environment support found.')

    options = {
        '--venv': 0,
        '--venv-system-site-packages': 0,
    }

    with tempdir() as inject_path:
        for version, path in venvs.items():
            create_interpreter_wrapper(os.path.join(path, 'bin', 'python'), os.path.join(inject_path, 'python%s' % version))

        python_interpreter = os.path.join(inject_path, 'python%s' % args.python_version)

        cmd = generate_command(args, python_interpreter, ANSIBLE_BIN_PATH, data_context().content.root, options, exclude, require)

        if isinstance(args, TestConfig):
            if args.coverage and not args.coverage_label:
                cmd += ['--coverage-label', 'venv']

        env = common_environment()

        with tempdir() as library_path:
            # expose ansible and ansible_test to the virtual environment (only required when running from an install)
            os.symlink(ANSIBLE_LIB_ROOT, os.path.join(library_path, 'ansible'))
            os.symlink(ANSIBLE_TEST_ROOT, os.path.join(library_path, 'ansible_test'))

            env.update(
                PATH=inject_path + os.path.pathsep + env['PATH'],
                PYTHONPATH=library_path,
            )

            with support_container_context(args, None) as containers:
                if containers:
                    cmd.extend(['--containers', json.dumps(containers.to_dict())])

                run_command(args, cmd, env=env)


def delegate_docker(args, exclude, require):
    """
    :type args: EnvironmentConfig
    :type exclude: list[str]
    :type require: list[str]
    """
    get_docker_command(required=True)  # fail early if docker is not available

    test_image = args.docker
    privileged = args.docker_privileged

    docker_pull(args, test_image)

    test_id = None
    success = False

    options = {
        '--docker': 1,
        '--docker-privileged': 0,
        '--docker-util': 1,
    }

    python_interpreter = get_python_interpreter(args, get_docker_completion(), args.docker_raw)

    pwd = '/root'
    ansible_root = os.path.join(pwd, 'ansible')

    if data_context().content.collection:
        content_root = os.path.join(pwd, data_context().content.collection.directory)
    else:
        content_root = ansible_root

    remote_results_root = os.path.join(content_root, data_context().content.results_path)

    cmd = generate_command(args, python_interpreter, os.path.join(ansible_root, 'bin'), content_root, options, exclude, require)

    if isinstance(args, TestConfig):
        if args.coverage and not args.coverage_label:
            image_label = args.docker_raw
            image_label = re.sub('[^a-zA-Z0-9]+', '-', image_label)
            cmd += ['--coverage-label', 'docker-%s' % image_label]

    if isinstance(args, IntegrationConfig):
        if not args.allow_destructive:
            cmd.append('--allow-destructive')

    cmd_options = []

    if isinstance(args, ShellConfig) or (isinstance(args, IntegrationConfig) and args.debug_strategy):
        cmd_options.append('-it')

    pypi_proxy_id, pypi_proxy_endpoint = run_pypi_proxy(args)

    if pypi_proxy_endpoint:
        cmd += ['--pypi-endpoint', pypi_proxy_endpoint]

    with tempfile.NamedTemporaryFile(prefix='ansible-source-', suffix='.tgz') as local_source_fd:
        try:
            create_payload(args, local_source_fd.name)

            test_options = [
                '--detach',
                '--volume', '/sys/fs/cgroup:/sys/fs/cgroup:ro',
                '--privileged=%s' % str(privileged).lower(),
            ]

            if args.docker_memory:
                test_options.extend([
                    '--memory=%d' % args.docker_memory,
                    '--memory-swap=%d' % args.docker_memory,
                ])

            docker_socket = '/var/run/docker.sock'

            if args.docker_seccomp != 'default':
                test_options += ['--security-opt', 'seccomp=%s' % args.docker_seccomp]

            if get_docker_hostname() != 'localhost' or os.path.exists(docker_socket):
                test_options += ['--volume', '%s:%s' % (docker_socket, docker_socket)]

            test_id = docker_run(args, test_image, options=test_options)

            setup_sh = read_text_file(os.path.join(ANSIBLE_TEST_DATA_ROOT, 'setup', 'docker.sh'))

            ssh_keys_sh = get_ssh_key_setup(SshKey(args))

            setup_sh += ssh_keys_sh
            shell = setup_sh.splitlines()[0][2:]

            docker_exec(args, test_id, [shell], data=setup_sh)

            # write temporary files to /root since /tmp isn't ready immediately on container start
            docker_put(args, test_id, local_source_fd.name, '/root/test.tgz')
            docker_exec(args, test_id, ['tar', 'oxzf', '/root/test.tgz', '-C', '/root'])

            # docker images are only expected to have a single python version available
            if isinstance(args, UnitsConfig) and not args.python:
                cmd += ['--python', 'default']

            # run unit tests unprivileged to prevent stray writes to the source tree
            # also disconnect from the network once requirements have been installed
            if isinstance(args, UnitsConfig):
                writable_dirs = [
                    os.path.join(content_root, ResultType.JUNIT.relative_path),
                    os.path.join(content_root, ResultType.COVERAGE.relative_path),
                ]

                docker_exec(args, test_id, ['mkdir', '-p'] + writable_dirs)
                docker_exec(args, test_id, ['chmod', '777'] + writable_dirs)
                docker_exec(args, test_id, ['chmod', '755', '/root'])
                docker_exec(args, test_id, ['chmod', '644', os.path.join(content_root, args.metadata_path)])

                docker_exec(args, test_id, ['useradd', 'pytest', '--create-home'])

                docker_exec(args, test_id, cmd + ['--requirements-mode', 'only'], options=cmd_options)

                container = docker_inspect(args, test_id)
                networks = container.get_network_names()

                if networks is not None:
                    for network in networks:
                        docker_network_disconnect(args, test_id, network)
                else:
                    display.warning('Network disconnection is not supported (this is normal under podman). '
                                    'Tests will not be isolated from the network. Network-related tests may misbehave.')

                cmd += ['--requirements-mode', 'skip']

                cmd_options += ['--user', 'pytest']

            try:
                with support_container_context(args, None) as containers:
                    if containers:
                        cmd.extend(['--containers', json.dumps(containers.to_dict())])

                    docker_exec(args, test_id, cmd, options=cmd_options)
                # docker_exec will throw SubprocessError if not successful
                # If we make it here, all the prep work earlier and the docker_exec line above were all successful.
                success = True
            finally:
                local_test_root = os.path.dirname(os.path.join(data_context().content.root, data_context().content.results_path))

                remote_test_root = os.path.dirname(remote_results_root)
                remote_results_name = os.path.basename(remote_results_root)
                remote_temp_file = os.path.join('/root', remote_results_name + '.tgz')

                try:
                    make_dirs(local_test_root)  # make sure directory exists for collections which have no tests

                    with tempfile.NamedTemporaryFile(prefix='ansible-result-', suffix='.tgz') as local_result_fd:
                        docker_exec(args, test_id, ['tar', 'czf', remote_temp_file, '--exclude', ResultType.TMP.name, '-C', remote_test_root,
                                                    remote_results_name])
                        docker_get(args, test_id, remote_temp_file, local_result_fd.name)
                        run_command(args, ['tar', 'oxzf', local_result_fd.name, '-C', local_test_root])
                except Exception as ex:  # pylint: disable=broad-except
                    if success:
                        raise  # download errors are fatal, but only if tests succeeded

                    # handle download error here to avoid masking test failures
                    display.warning('Failed to download results while handling an exception: %s' % ex)
        finally:
            if pypi_proxy_id:
                docker_rm(args, pypi_proxy_id)

            if test_id:
                if args.docker_terminate == 'always' or (args.docker_terminate == 'success' and success):
                    docker_rm(args, test_id)


def delegate_remote(args, exclude, require):
    """
    :type args: EnvironmentConfig
    :type exclude: list[str]
    :type require: list[str]
    """
    remote = args.parsed_remote

    core_ci = AnsibleCoreCI(args, remote.platform, remote.version, stage=args.remote_stage, provider=args.remote_provider, arch=remote.arch)
    success = False

    ssh_options = []
    content_root = None

    try:
        core_ci.start()
        core_ci.wait()

        python_version = get_python_version(args, get_remote_completion(), args.remote)
        python_interpreter = None

        if remote.platform == 'windows':
            # Windows doesn't need the ansible-test fluff, just run the SSH command
            manage = ManageWindowsCI(core_ci)
            manage.setup(python_version)

            cmd = ['powershell.exe']
        elif isinstance(args, ShellConfig) and args.raw:
            manage = ManagePosixCI(core_ci)
            manage.setup(python_version)

            cmd = create_shell_command(['sh'])
        else:
            manage = ManagePosixCI(core_ci)
            pwd = manage.setup(python_version)

            options = {
                '--remote': 1,
            }

            python_interpreter = get_python_interpreter(args, get_remote_completion(), args.remote)

            ansible_root = os.path.join(pwd, 'ansible')

            if data_context().content.collection:
                content_root = os.path.join(pwd, data_context().content.collection.directory)
            else:
                content_root = ansible_root

            cmd = generate_command(args, python_interpreter, os.path.join(ansible_root, 'bin'), content_root, options, exclude, require)

            if isinstance(args, TestConfig):
                if args.coverage and not args.coverage_label:
                    cmd += ['--coverage-label', 'remote-%s-%s' % (remote.platform, remote.version)]

            if isinstance(args, IntegrationConfig):
                if not args.allow_destructive:
                    cmd.append('--allow-destructive')

            # remote instances are only expected to have a single python version available
            if isinstance(args, UnitsConfig) and not args.python:
                cmd += ['--python', 'default']

        try:
            ssh_con = core_ci.connection
            ssh = SshConnectionDetail(core_ci.name, ssh_con.hostname, ssh_con.port, ssh_con.username, core_ci.ssh_key.key, python_interpreter)

            with support_container_context(args, ssh) as containers:
                if containers:
                    cmd.extend(['--containers', json.dumps(containers.to_dict())])

                manage.ssh(cmd, ssh_options)

            success = True
        finally:
            download = False

            if remote.platform != 'windows':
                download = True

            if isinstance(args, ShellConfig):
                if args.raw:
                    download = False

            if download and content_root:
                local_test_root = os.path.dirname(os.path.join(data_context().content.root, data_context().content.results_path))

                remote_results_root = os.path.join(content_root, data_context().content.results_path)
                remote_results_name = os.path.basename(remote_results_root)
                remote_temp_path = os.path.join('/tmp', remote_results_name)

                # AIX cp and GNU cp provide different options, no way could be found to have a common
                # pattern and achieve the same goal
                cp_opts = '-hr' if remote.platform == 'aix' else '-a'

                try:
                    command = 'rm -rf {0} && mkdir {0} && cp {1} {2}/* {0}/ && chmod -R a+r {0}'.format(remote_temp_path, cp_opts, remote_results_root)

                    manage.ssh(command, capture=True)  # pylint: disable=unexpected-keyword-arg
                    manage.download(remote_temp_path, local_test_root)
                except Exception as ex:  # pylint: disable=broad-except
                    if success:
                        raise  # download errors are fatal, but only if tests succeeded

                    # handle download error here to avoid masking test failures
                    display.warning('Failed to download results while handling an exception: %s' % ex)
    finally:
        if args.remote_terminate == 'always' or (args.remote_terminate == 'success' and success):
            core_ci.stop()


def generate_command(args, python_interpreter, ansible_bin_path, content_root, options, exclude, require):
    """
    :type args: EnvironmentConfig
    :type python_interpreter: str | None
    :type ansible_bin_path: str
    :type content_root: str
    :type options: dict[str, int]
    :type exclude: list[str]
    :type require: list[str]
    :rtype: list[str]
    """
    options['--color'] = 1

    cmd = [os.path.join(ansible_bin_path, 'ansible-test')]

    if python_interpreter:
        cmd = [python_interpreter] + cmd

    # Force the encoding used during delegation.
    # This is only needed because ansible-test relies on Python's file system encoding.
    # Environments that do not have the locale configured are thus unable to work with unicode file paths.
    # Examples include FreeBSD and some Linux containers.
    env_vars = dict(
        LC_ALL='en_US.UTF-8',
        ANSIBLE_TEST_CONTENT_ROOT=content_root,
    )

    env_args = ['%s=%s' % (key, env_vars[key]) for key in sorted(env_vars)]

    cmd = ['/usr/bin/env'] + env_args + cmd

    cmd += list(filter_options(args, sys.argv[1:], options, exclude, require))
    cmd += ['--color', 'yes' if args.color else 'no']

    if args.requirements:
        cmd += ['--requirements']

    if isinstance(args, ShellConfig):
        cmd = create_shell_command(cmd)
    elif isinstance(args, SanityConfig):
        base_branch = args.base_branch or get_ci_provider().get_base_branch()

        if base_branch:
            cmd += ['--base-branch', base_branch]

    return cmd


def filter_options(args, argv, options, exclude, require):
    """
    :type args: EnvironmentConfig
    :type argv: list[str]
    :type options: dict[str, int]
    :type exclude: list[str]
    :type require: list[str]
    :rtype: collections.Iterable[str]
    """
    options = options.copy()

    options['--requirements'] = 0
    options['--truncate'] = 1
    options['--redact'] = 0
    options['--no-redact'] = 0

    if isinstance(args, TestConfig):
        options.update({
            '--changed': 0,
            '--tracked': 0,
            '--untracked': 0,
            '--ignore-committed': 0,
            '--ignore-staged': 0,
            '--ignore-unstaged': 0,
            '--changed-from': 1,
            '--changed-path': 1,
            '--metadata': 1,
            '--exclude': 1,
            '--require': 1,
        })
    elif isinstance(args, SanityConfig):
        options.update({
            '--base-branch': 1,
        })

    if isinstance(args, IntegrationConfig):
        options.update({
            '--no-temp-unicode': 0,
            '--no-pip-check': 0,
        })

    if isinstance(args, (NetworkIntegrationConfig, WindowsIntegrationConfig)):
        options.update({
            '--inventory': 1,
        })

    remaining = 0

    for arg in argv:
        if not arg.startswith('-') and remaining:
            remaining -= 1
            continue

        remaining = 0

        parts = arg.split('=', 1)
        key = parts[0]

        if key in options:
            remaining = options[key] - len(parts) + 1
            continue

        yield arg

    for arg in args.delegate_args:
        yield arg

    for target in exclude:
        yield '--exclude'
        yield target

    for target in require:
        yield '--require'
        yield target

    if isinstance(args, TestConfig):
        if args.metadata_path:
            yield '--metadata'
            yield args.metadata_path

    yield '--truncate'
    yield '%d' % args.truncate

    if args.redact:
        yield '--redact'
    else:
        yield '--no-redact'

    if isinstance(args, IntegrationConfig):
        if args.no_temp_unicode:
            yield '--no-temp-unicode'

        if not args.pip_check:
            yield '--no-pip-check'
