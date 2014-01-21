import os
import re
import subprocess
import time

class MinecraftServerManager(object):
    LOG_READ_WAIT = 1

    def __init__(self, interface, log_path):
        self.interface = interface
        self.log_path = log_path
        self.log = open(log_path, 'r')

    def exec_cmd(self, command):
        self.interface.clear_input()
        self.interface.send(command + '\n')

    def exec_check_log(self, command, success, failure, timeout=-1):
        self.log.seek(0, os.SEEK_END)
        self.interface.clear_input()
        self.interface.send(command + '\n')
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

class TmuxPaneInterface(object):
    BACKSPACE = '\x7F'

    def __init__(self, tmux, session, pane, socket_path=None):
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
        rc, output = self.tmux.exec_cmd(tmux_pane_cmd)
        return (rc, output)

    def send(self, s):
        self._exec_cmd(['send-keys', s])

    @property
    def target(self):
        return '{}:{}'.format(self.session, self.pane)

class Tmux(object):
    SOCKET_PATH_OPT = '-S'
    TARGET_OPT = '-t'

    def __init__(self, tmux_path='/usr/bin/tmux'):
        self.tmux_path = tmux_path

    def exec_cmd(self, command):
        tmux_command = [self.tmux_path]
        tmux_command.extend(command)
        output = None
        rc = 0
        try:
            output = subprocess.check_output(tmux_command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            rc = e.returncode
            output = e.output
        return (rc, output)

class ServerCommandError(Exception): pass
class ServerCommandTimeout(ServerCommandError): pass
