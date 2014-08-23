#!/usr/bin/python3

# appinterface.py - manager for interfaces to command-line applications
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

import importlib
import glob
import os.path
import sys

class AppInterfaceManager(object):
    def __init__(self, interface_dir='interfaces'):
        self.app_interfaces = dict()
        if not os.path.isabs(interface_dir):
            interface_dir = os.path.join(os.path.dirname(__file__),
                interface_dir)
        self.interface_dir = interface_dir

    def get(self, name):
        interface = None
        try:
            interface = self.app_interfaces[name.casefold()]
        except KeyError as e:
            raise InvalidServerInterface(("`{}' is not a valid interface "
                "name").format(name)) from e
        return interface

    def register(self, cls):
        self.app_interfaces[cls.__name__.casefold()] = cls
        return cls

    def import_interfaces(self):
        sys.path.append(os.path.dirname(self.interface_dir))
        d = self.interface_dir
        for module in glob.glob(os.path.join(d, '*.py')):
            import_namespace = '{}.{}'.format(os.path.basename(d),
                os.path.basename(module[:-3]))
            importlib.import_module(import_namespace)


class InvalidServerInterface(Exception): pass
class AppInterfaceError(Exception): pass

def register(*args, **kwargs):
    return _mgr.register(*args, **kwargs)

def get(*args, **kwargs):
    return _mgr.get(*args, **kwargs)

_mgr = AppInterfaceManager()
