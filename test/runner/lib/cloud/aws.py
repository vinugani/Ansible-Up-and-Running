"""AWS plugin for integration tests."""
from __future__ import absolute_import, print_function

import os

from lib.util import (
    ApplicationError,
    display,
    is_shippable,
    ConfigParser,
)

from lib.cloud import (
    CloudProvider,
    CloudEnvironment,
    CloudEnvironmentConfig,
)

from lib.core_ci import (
    AnsibleCoreCI,
)


class AwsCloudProvider(CloudProvider):
    """AWS cloud provider plugin. Sets up cloud resources before delegation."""
    def filter(self, targets, exclude):
        """Filter out the cloud tests when the necessary config and resources are not available.
        :type targets: tuple[TestTarget]
        :type exclude: list[str]
        """
        if os.path.isfile(self.config_static_path):
            return

        aci = self._create_ansible_core_ci()

        if os.path.isfile(aci.ci_key):
            return

        if is_shippable():
            return

        super(AwsCloudProvider, self).filter(targets, exclude)

    def setup(self):
        """Setup the cloud resource before delegation and register a cleanup callback."""
        super(AwsCloudProvider, self).setup()

        aws_config_path = os.path.expanduser('~/.aws')

        if os.path.exists(aws_config_path) and not self.args.docker and not self.args.remote:
            raise ApplicationError('Rename "%s" or use the --docker or --remote option to isolate tests.' % aws_config_path)

        if not self._use_static_config():
            self._setup_dynamic()

    def _setup_dynamic(self):
        """Request AWS credentials through the Ansible Core CI service."""
        display.info('Provisioning %s cloud environment.' % self.platform, verbosity=1)

        config = self._read_config_template()

        aci = self._create_ansible_core_ci()

        response = aci.start()

        if not self.args.explain:
            credentials = response['aws']['credentials']

            values = dict(
                ACCESS_KEY=credentials['access_key'],
                SECRET_KEY=credentials['secret_key'],
                SECURITY_TOKEN=credentials['session_token'],
                REGION='us-east-1',
            )

            config = self._populate_config_template(config, values)

        self._write_config(config)

    def _create_ansible_core_ci(self):
        """
        :rtype: AnsibleCoreCI
        """
        return AnsibleCoreCI(self.args, 'aws', 'sts', persist=False, stage=self.args.remote_stage, provider=self.args.remote_provider)


class AwsCloudEnvironment(CloudEnvironment):
    """AWS cloud environment plugin. Updates integration test environment after delegation."""
    def get_environment_config(self):
        """
        :rtype: CloudEnvironmentConfig
        """
        parser = ConfigParser()
        parser.read(self.config_path)

        ansible_vars = dict(
            resource_prefix=self.resource_prefix,
        )

        ansible_vars.update(dict(parser.items('default')))

        if 'aws_cleanup' not in ansible_vars:
            ansible_vars['aws_cleanup'] = not self.managed

        env_vars = {'ANSIBLE_DEBUG_BOTOCORE_LOGS': 'True'}

        return CloudEnvironmentConfig(
            env_vars=env_vars,
            ansible_vars=ansible_vars,
            callback_plugins=['aws_resource_actions'],
        )

    def on_failure(self, target, tries):
        """
        :type target: TestTarget
        :type tries: int
        """
        if not tries and self.managed:
            display.notice('If %s failed due to permissions, the IAM test policy may need to be updated. '
                           'For help, consult @mattclay or @gundalow on GitHub or #ansible-devel on IRC.' % target.name)
