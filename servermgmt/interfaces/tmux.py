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

import shlex
import subprocess
import sys

import appinterface


@appinterface.register
class TmuxInterface(object):
    """An interface that allows programmatic interaction to applications
    running inside tmux.
    """

    BACKSPACE = '\x7F'
    SOCKET_PATH_OPT = '-S'
    TARGET_OPT = '-t'

    def __init__(self, session, window, tmux_path='/usr/bin/tmux',
                 socket_path=None):
        """Initializes a TmuxInterface."""
        self.session = session
        self.window = window
        self.tmux_path = tmux_path
        self.socket_path = socket_path

    def clear_input(self):
        """Attempts to clear any program input by sending lots of backspaces."""
        self.send(self.BACKSPACE * 500)

    def exec_window_cmd(self, command):
        """Executes a tmux command (e.g. send-keys) against the target window."""
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
        """Executes a tmux subcommand."""
        tmux_command = [self.tmux_path]
        tmux_command.extend(command)
        # First, we need to quote each part of tmux_command so that
        # the arguments are not interpreted specially by the shell.
        quoted_command = ' '.join([shlex.quote(s) for s in tmux_command])
        # Then, we need to take the entire quoted command and quote it
        # *again* since it will be passed to $SHELL -c.
        shell_cmd = "$SHELL -l -c {0}".format(shlex.quote(quoted_command))
        output = None
        try:
            # Eww, running with shell=True. Unfortunately, this seems to be the
            # easiest way to run in the user's environment.
            output = subprocess.check_output(
                shell_cmd, stderr=subprocess.STDOUT, shell=True
            )
        except subprocess.CalledProcessError as e:
            raise TmuxCommandError(e.returncode, e.cmd, e.output)
        return output

    def invoke_interface(self, command):
        """Invokes command inside a tmux session."""
        try:
            cmd = [
                'new-session', '-d', '-s', self.session, '-n',
                self.window, command
            ]
            self.exec_tmux_cmd(cmd)
        except TmuxCommandError:
            cmd = [
                'new-window', '-a', '-n', self.window, '-t',
                '{}:0'.format(self.session), command
            ]
            self.exec_tmux_cmd(cmd)

    @classmethod
    def read_config_options(cls, configparser, section):
        """Given a configparser, reads and returns configuration options
        necessary to instantiate a TmuxInterface object.
        """
        session = configparser.get(section, 'session', fallback='0')
        window = configparser.get(section, 'window', fallback='0')
        return (session, window)

    def send(self, s):
        """Sends the keys given by s to the target tmux window."""
        self.exec_window_cmd(['send-keys', s])

    @property
    def target(self):
        """Returns an identifer suitable for uniquely identifying the tmux
        window targeted by this object (via tmux option -t)."""
        return '{}:{}'.format(self.session, self.window)


class TmuxCommandError(subprocess.CalledProcessError,
    appinterface.AppInterfaceError): pass
