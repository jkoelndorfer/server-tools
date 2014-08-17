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

import imp
import glob
import os.path
import sys

class AppInterfaceManager(object):
    def __init__(self, interface_dir='interfaces'):
        self.app_interfaces = dict()
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
        sys.path.append(os.path.dirname(__file__))
        for module in glob.glob(os.path.join(self.interface_dir, '*.py')):
            import_name = os.path.basename(module[:-3])
            try:
                imp.load_source(import_name, module)
            except:
                # TODO: implement some better error handling here
                pass


class InvalidServerInterface(Exception): pass
class AppInterfaceError(Exception): pass

mgr = AppInterfaceManager()

def register(*args, **kwargs):
    return mgr.register(*args, **kwargs)

def get(*args, **kwargs):
    return mgr.get(*args, **kwargs)

mgr.import_interfaces()
