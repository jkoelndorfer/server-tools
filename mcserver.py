# mcserver.py - library to manage a Minecraft server
# Copyright (C) 2014  John Koelndorfer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import configparser
import os
import re
import subprocess
import time

import appinterface

class MinecraftServerManager(object):
    LOG_READ_WAIT = 1

    def __init__(self, interface, server_jar, user=None, log_path=None,
        java_path='java', java_options='-Xmx2G -Xms2G', server_args='nogui'):
        self.interface = interface
        self.server_jar = server_jar
        self.user = user
        if log_path is None:
            log_path = os.path.join(os.path.split(server_jar)[0], 'server.log')
        self.log = open(log_path, 'r')
        self.java_path = java_path
        self.java_options = java_options
        self.server_args = server_args

    def exec_cmd(self, command):
        self.interface.clear_input()
        self.interface.send(command + '\n')

    def exec_check_log(self, command, success, failure, timeout=-1):
        self.log.seek(0, os.SEEK_END)
        self.exec_cmd(command)
        check_log_args = [success, failure]
        if timeout != -1:
            check_log_args.append(timeout)
        self.check_log(*check_log_args)

    def check_log(self, success_re, failure_re, timeout=30):
        start_time = time.time()
        timeout_time = None
        if timeout is not None:
            timeout_time = time.time() + timeout
        while True:
            current_time = time.time()
            if timeout_time is not None:
                if current_time < start_time:
                    # Something weird happened with the system time.
                    # We're gonna bail just to be safe.
                    raise ServerCommandTimeout()
                if current_time > timeout_time:
                    raise ServerCommandTimeout()
            # This seems wonky and quite non-Pythonic, but it is apparently the
            # best way to do it.
            #
            # `for line in f' doesn't seem to work after we have seek()ed.
            # readlines() could potentially return a massive list.
            # xreadlines() will be gone in Python 3.
            while True:
                line = self.log.readline()
                if line == '':
                    break
                elif re.search(success_re, line):
                    return
                elif failure_re is not None and re.search(failure_re, line):
                    raise ServerCommandError()
            time.sleep(self.LOG_READ_WAIT)

    @classmethod
    def check_log_regex(cls, strings):
        escaped_strings = [re.escape(x) for x in strings]
        return '(' + '|'.join(escaped_strings) + ')'

    def force_save(self):
        save_success_messages = [
            'Saved the world',
            'Save complete'
        ]
        save_failure_messages = [
            'Saving failed'
        ]
        save_success_re = self.check_log_regex(save_success_messages)
        save_failure_re = self.check_log_regex(save_failure_messages)
        self.exec_check_log('save-all', save_success_re, save_failure_re)

    def save_on(self):
        self._set_save('on')

    def save_off(self):
        self._set_save('off')

    def _set_save(self, state):
        save_toggle_messages = {
            'on': [
                'Turned on world auto-saving',
                'Saving is already turned on',
                'Enabled level saving'
            ],
            'off': [
                'Turned off world auto-saving',
                'Saving is already turned off',
                'Disabled level saving'
            ]
        }
        success_re = self.check_log_regex(save_toggle_messages[state])
        cmd = 'save-{}'.format(state)
        self.exec_check_log(cmd, success_re, None)

    @property
    def server_launch_cmd(self):
        return '{java} {java_options} -jar {server_jar} {server_args}'.format(
            java=self.java_path, java_options=self.java_options,
            server_jar=self.server_jar, server_args=self.server_args
        )

    @property
    def server_dir(self):
        return os.path.split(self.server_jar)[0]

    def start(self):
        old_cwd = os.getcwd()
        os.chdir(self.server_dir)
        try:
            self.interface.invoke_interface(self.server_launch_cmd)
        finally:
            os.chdir(old_cwd)

    def stop(self, do_save=False):
        if do_save:
            self.save_off()
            self.force_save()
        self.exec_cmd('stop')


class Util(object):
    @staticmethod
    def config_argparse_common(arg_parser):
        p = arg_parser
        p.add_argument(
            '-l', '--server-log', default=None,
            help='Path to the Minecraft server log.'
        )
        p.add_argument(
            '-s', '--tmux-session', default='0',
            help='Name of the tmux session containing the window specified by '
            '-w.'
        )
        p.add_argument(
            '-w', '--tmux-window', default='0',
            help='Name or index of the tmux window the server is running in.'
        )
        p.add_argument(
            '-S', '--tmux-socket-path', default=None,
            help='Path to the socket tmux will connect to.'
        )

    @staticmethod
    def load_config(config_path, section=None):
        config = configparser.ConfigParser()
        config.read(config_path)
        if section is None:
            section = config.sections()[0]

        interface_type = config.get(section, 'interface')
        interface_class = appinterface.get(interface_type)
        interface_args = interface_class.read_config_options(config, section)
        interface = interface_class(*interface_args)

        server_kwargs = dict()
        for arg in ['server_jar', 'user', 'log_path', 'java_path',
            'java_options', 'server_args']:
            config_arg_name = arg.replace('_', ' ')
            try:
                server_kwargs[arg] = config.get(section, config_arg_name)
            except configparser.NoOptionError:
                # If we don't get the config parameters we need,
                # MinecraftServerManager can raise an exception
                pass
        return MinecraftServerManager(interface, **server_kwargs)

class ServerCommandError(Exception): pass
class ServerCommandTimeout(ServerCommandError): pass
