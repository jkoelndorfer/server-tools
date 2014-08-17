#!/usr/bin/python3

# tmux.py - tmux interface to command-line applications
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

import subprocess
import sys

import appinterface


@appinterface.register
class TmuxInterface(object):
    BACKSPACE = '\x7F'
    SOCKET_PATH_OPT = '-S'
    TARGET_OPT = '-t'

    def __init__(self, session, window, tmux_path='/usr/bin/tmux',
                 socket_path=None):
        self.session = session
        self.window = window
        self.tmux_path = tmux_path
        self.socket_path = socket_path

    def clear_input(self):
        self.send(self.BACKSPACE * 500)

    def exec_window_cmd(self, command):
        tmux_window_cmd = []
        if self.socket_path is not None:
            tmux_window_cmd.extend([self.SOCKET_PATH_OPT, self.socket_path])
        # tmux is picky about argument ordering - we need to make sure -t
        # appears immediately after the command.
        tmux_window_cmd.append(command[0])
        tmux_window_cmd.extend([self.TARGET_OPT, self.target])
        tmux_window_cmd.extend(command[1:])
        output = self.exec_tmux_cmd(tmux_window_cmd)
        return output

    def exec_tmux_cmd(self, command):
        tmux_command = [self.tmux_path]
        tmux_command.extend(command)
        output = None
        try:
            output = subprocess.check_output(
                tmux_command, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            raise TmuxCommandError(e.returncode, e.cmd, e.output)
        return output

    def invoke_interface(self, command):
        try:
            cmd = [
                'new-session', '-d', '-s', self.session, '-n',
                self.window, command
            ]
            self.exec_tmux_cmd(cmd)
        except TmuxCommandError:
            try:
                cmd = [
                    'new-window', '-a', '-n', self.window, '-t',
                    '{}:0'.format(self.session), command
                ]
                self.exec_tmux_cmd(cmd)
            except TmuxCommandError as e:
                raise ServerStartError(str(e))

    @classmethod
    def read_config_options(cls, configparser, section):
        session = configparser.get(section, 'session', fallback='0')
        window = configparser.get(section, 'window', fallback='0')
        return (session, window)

    def send(self, s):
        self.exec_window_cmd(['send-keys', s])

    @property
    def target(self):
        return '{}:{}'.format(self.session, self.window)


class TmuxCommandError(subprocess.CalledProcessError,
    appinterface.AppInterfaceError): pass
