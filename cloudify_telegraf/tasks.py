########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import os
import sys
import shlex
import tempfile
import subprocess
import pkg_resources

import sh
import jinja2
import distro

from cloudify import ctx
from cloudify import exceptions
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError


@operation
def install(config_inputs, download_url=None, config_file=None, **_):
    return Telegraf().install(config_inputs, download_url, config_file)


@operation
def start(**_):
    return Telegraf().start()


@operation
def stop(**_):
    return Telegraf().stop()


@operation
def remove(**_):
    return Telegraf().remove()


class Telegraf(object):
    def __init__(self):
        self.config_path = '/etc/telegraf/telegraf.conf'
        self.setup_path = '/opt/telegraf'

    def install(self, config_inputs, download_url=None, config_file=None):
        if 'linux' not in sys.platform:
            raise exceptions.NonRecoverableError(
                'Error! Telegraf-plugin is available only on linux')
        if os.path.isfile(self.setup_path):
            raise ValueError(format("Error! {0} file already exists, can't create dir.",
                                    self.setup_path))
        url = download_url or self._download_url()
        file_path = self._download_file(url)
        self._install(file_path)
        self._update_global_tags(config_inputs.get('global_tags', {}))
        self._configure(config_file, config_inputs)

    def remove(self):
        if 'linux' not in sys.platform:
            raise exceptions.NonRecoverableError(
                'Error! Telegraf-plugin is available only on linux')
        if not os.path.isfile(self.setup_path):
            raise ValueError(format("Error! {0} file not exists.",
                                    self.setup_path))
        self._remove()

    def start(self):
        ctx.logger.info('Starting telegraf service...')
        if os.path.exists('/usr/bin/systemctl'):
            proc = self._run('sudo systemctl restart telegraf')
            self._run('sudo systemctl enable telegraf')
            self._run('sudo systemctl daemon-reload')
        else:
            proc = self._run('sudo service telegraf restart')
            self._run('sudo service enable telegraf')
            self._run('sudo service daemon-reload')
        ctx.logger.info('Telegraf service is up!')
        return proc.aggr_stdout

    def stop(self):
        ctx.logger.info('Stopping telegraf service...')
        if os.path.exists('/usr/bin/systemctl'):
            proc = self._run('sudo systemctl stop telegraf')
        else:
            proc = self._run('sudo service stop restart')
        ctx.logger.info('Telegraf service is up!')
        return proc.aggr_stdout

    @staticmethod
    def _download_url():
        linux_distribution = distro.id()
        url_base = 'https://dl.influxdata.com/telegraf/releases/'
        if linux_distribution in {'ubuntu', 'debian'}:
            download_url = os.path.join(url_base, 'telegraf_1.4.0-1_amd64.deb')
        elif linux_distribution in {'centos', 'redhat'}:
            download_url = os.path.join(url_base, 'telegraf-1.4.0-1.x86_64.rpm')
        else:
            raise exceptions.NonRecoverableError(
                '''Error! distribution is not supported.
                Ubuntu, Debian, Centos and Redhat are supported currently''')
        return download_url

    @staticmethod
    def _download_file(source, destination=None):
        ctx.logger.info('Downloading Telegraf setup file: {0}'.format(source))
        if not destination:
            fd, destination = tempfile.mkstemp()
            os.close(fd)
            _, file_extension = os.path.splitext(source)
            destination += file_extension
        curl = sh.curl.bake('--fail', '--silent', '--show-error', '--create-dir')
        curl('--location', source, '--output', destination)
        ctx.logger.debug('downloaded `{0}` to `{1}`'.format(source, destination))
        return destination

    @staticmethod
    def _install(installation_file):
        ctx.logger.info('Installing Telegraf, installation_file: {0}'.format(installation_file))
        linux_distribution = distro.id()
        if linux_distribution in {'ubuntu', 'debian'}:
            install_cmd = 'sudo dpkg -i {0}'.format(installation_file)
        elif linux_distribution in {'centos', 'redhat'}:
            install_cmd = 'sudo yum install -y {0}'.format(installation_file)
        else:
            raise exceptions.NonRecoverableError(
                '''Error! distribution is not supported.
                Ubuntu, Debian, Centos and Redhat are supported currently''')
        Telegraf._run(install_cmd)
        ctx.logger.info('Telegraf service was installed...')

    @staticmethod
    def _remove():
        ctx.logger.info('Removing Telegraf service')
        linux_distribution = distro.id()
        if linux_distribution in {'ubuntu', 'debian'}:
            remove_cmd = 'sudo dpkg --remove telegraf'
        elif linux_distribution in {'centos', 'redhat'}:
            remove_cmd = 'sudo yum remove telegraf'
        else:
            raise exceptions.NonRecoverableError(
                '''Error! distribution is not supported.
                Ubuntu, Debian, Centos and Redhat are supported currently''')
        Telegraf._run(remove_cmd)
        ctx.logger.info('Telegraf service was removed...')

    @staticmethod
    def _run(command):
        if isinstance(command, str):
            command = shlex.split(command)
        stderr = subprocess.PIPE
        stdout = subprocess.PIPE
        ctx.logger.debug('Running: {0}'.format(command))
        proc = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        proc.aggr_stdout, proc.aggr_stderr = proc.communicate()
        if proc.returncode != 0:
            command_str = ' '.join(command)
            ctx.logger.error('Failed running command: {0} ({1}).'.format(
                command_str, proc.aggr_stderr))
            sys.exit(1)
        return proc

    def _configure(self, telegraf_config_file=None, template_config=None, **kwargs):
        ctx.logger.info('Configuring Telegraf... template config: {0}'.format(template_config))
        destination_file = os.path.join(tempfile.gettempdir(), 'telegraf.conf')
        if telegraf_config_file:
            try:
                ctx.download_resource_and_render(telegraf_config_file,
                                                 destination_file,
                                                 template_config)
            except:
                raise ValueError(
                    "wrong inputs provided! can't render configuration file")
        else:
            config_file = pkg_resources.resource_string('cloudify_telegraf',
                                                        'resources/telegraf.conf')
            configuration = jinja2.Template(config_file)
            try:
                with open(destination_file, 'w') as f:
                    f.write(configuration.render(template_config))
            except:
                raise ValueError(
                    "wrong inputs provided! can't render configuration file")
        Telegraf._run('sudo mv {0} {1}'.format(destination_file, self.config_path))

        try:
            Telegraf._run('telegraf -config {0} -test'.format(self.config_path))
        except:
            raise ValueError(
                "wrong inputs prodided! configuration file is invalid: {0}"
                "".format(self.config_path))
        ctx.logger.info('telegraf.conf was configured...')

    @staticmethod
    def _update_global_tags(global_tags):
        replacements = {
            'CTX_DEPLOYMENT_ID': ctx.deployment.id,
            'CTX_TENANT_NAME': ctx.tenant_name,
            'CTX_HOST_PRIVATE_IP': ctx.instance.host_ip
        }
        for key, value in global_tags.iteritems():
            if value in replacements.keys():
                global_tags[key] = replacements[value]
