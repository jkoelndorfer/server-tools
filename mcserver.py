import os
import re
import subprocess
import time

class MinecraftServerManager(object):
    LOG_READ_WAIT = 1

    def __init__(self, interface, log_path=None):
        self.interface = interface
        self.log = None
        if log_path is not None:
            self.log = open(log_path, 'r')

    def exec_cmd(self, command):
        self.interface.clear_input()
        self.interface.send(command + '\n')

    def exec_check_log(self, command, success, failure, timeout=-1):
        self.interface.clear_input()
        self.interface.send(command + '\n')
        check_log_args = [success, failure]
        if timeout != -1:
            check_log_args.append(timeout)
        self.check_log(*check_log_args)

    def check_log(self, success_re, failure_re, timeout=30):
        if self.log is None:
            raise LogNotSpecifiedError('log must not be None to use check_log()')
        self.log.seek(0, os.SEEK_END)
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

    def force_save(self):
        self.exec_check_log('save-all', 'Saved the world', 'Saving failed')

    def save_on(self):
        self._set_save('on')

    def save_off(self):
        self._set_save('off')

    def _set_save(self, state):
        save_toggle_done = [x.format(state) for x in [
            'Turned {} world auto-saving',
            'Saving is already turned {}'
        ]]
        success_re = '({})'.format('|'.join(save_toggle_done))
        cmd = 'save-{}'.format(state)
        self.exec_check_log(cmd, success_re, None)

class Tmux(object):
    SOCKET_PATH_OPT = '-S'
    TARGET_OPT = '-t'

    def __init__(self, tmux_path='/usr/bin/tmux'):
        self.tmux_path = tmux_path

    def exec_cmd(self, command):
        tmux_command = [self.tmux_path]
        tmux_command.extend(command)
        output = None
        try:
            output = subprocess.check_output(tmux_command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise TmuxCommandError(e.returncode, e.cmd, e.output)
        return output

class TmuxPaneInterface(object):
    BACKSPACE = '\x7F'

    def __init__(self, session, pane, tmux=Tmux(), socket_path=None):
        self.tmux = tmux
        self.session = session
        self.pane = pane
        self.socket_path = socket_path

    def clear_input(self):
        self._exec_cmd(['send-keys', self.BACKSPACE * 500])

    def _exec_cmd(self, command):
        tmux_pane_cmd = []
        if self.socket_path is not None:
            tmux_pane_cmd.extend([self.tmux.SOCKET_PATH_OPT, self.socket_path])
        # tmux is picky about argument ordering - we need to make sure -t
        # appears immediately after the command.
        tmux_pane_cmd.append(command[0])
        tmux_pane_cmd.extend([self.tmux.TARGET_OPT, self.target])
        tmux_pane_cmd.extend(command[1:])
        output = self.tmux.exec_cmd(tmux_pane_cmd)
        return output

    def send(self, s):
        self._exec_cmd(['send-keys', s])

    @property
    def target(self):
        return '{}:{}'.format(self.session, self.pane)

class Util(object):
    @staticmethod
    def config_argparse_common(arg_parser):
        p = arg_parser
        p.add_argument('-l', '--server-log', default=None,
            help='Path to the Minecraft server log.'
        )
        p.add_argument('-s', '--tmux-session', default='0',
            help='Name of the tmux session containing the pane specified by -p.'
        )
        p.add_argument('-p', '--tmux-pane', default='0',
            help='Name or index of the tmux pane the server is running in.'
        )
        p.add_argument('-S', '--tmux-socket-path', default=None,
            help='Path to the socket tmux will connect to.'
        )

class LogNotSpecifiedError(Exception): pass
class ServerCommandError(Exception): pass
class ServerCommandTimeout(ServerCommandError): pass
class TmuxCommandError(subprocess.CalledProcessError): pass
