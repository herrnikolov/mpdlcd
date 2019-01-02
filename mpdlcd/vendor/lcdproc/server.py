# Copyright (c) 2015, JingleManSweep
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import telnetlib
import urllib.parse
import select

from .screen import Screen


class Server(object):
    """ LCDproc Server Object """

    def __init__(self, hostname="localhost", port=13666, debug=False):
        """ Constructor """

        self.debug = debug
        self.hostname = hostname
        self.port = port
        self.tn = telnetlib.Telnet(self.hostname, self.port)
        self.server_info = dict()
        self.screens = dict()
        self.keys = list()

    def start_session(self):
        """ Start Session """

        response = self.request("hello")
        bits = response.split(" ")
        self.server_info.update({
            "server_version": bits[2],
            "protocol_version": bits[4],
            "screen_width": int(bits[7]),
            "screen_height": int(bits[9]),
            "cell_width": int(bits[11]),
            "cell_height": int(bits[13])
        })
        return response

    def request(self, command_string):
        """ Request """

        self.tn.write((command_string + "\n").encode())
        if self.debug:
            print("Telnet Request:  %s" % (command_string))
        while True:
            response = urllib.parse.unquote(self.tn.read_until(b"\n").decode())
            if "success" in response:   # Normal successful reply
                break
            if "huh" in response:       # Something went wrong
                break
            if "connect" in response:   # Special reply to "hello"
                break
            # TODO Keep track of which screen is displayed
            # Try again if response was key, menu or visibility notification.
        if "huh" in response or self.debug:
            print("Telnet Response: %s" % (response[:-1]))
        return response

    def poll(self):
        """
        Poll

        Check for a non-response string generated by LCDd and return any string read.
        LCDd generates strings for key presses, menu events & screen visibility changes.
        """
        if select.select([self.tn], [], [], 0) == ([self.tn], [], []):
            response = urllib.parse.unquote(self.tn.read_until(b"\n").decode())
            if self.debug:
                print("Telnet Poll: %s" % (response[:-1]))
            # TODO Keep track of which screen is displayed
            return response
        else:
            return None

    def add_screen(self, ref):

        """ Add Screen """

        if ref not in self.screens:
            screen = Screen(self, ref)
            screen.clear()              # TODO Check this is needed, new screens should be clear.
            self.screens[ref] = screen
            return self.screens[ref]

    def del_screen(self, ref):
        """ Delete/Remove Screen """
        self.request("screen_del %s" % (ref))
        del(self.screens[ref])

    def add_key(self, ref, mode="shared"):
        """
        Add a key.

        (ref)
        Return key name or None on error
        """
        if ref not in self.keys:
            response = self.request("client_add_key %s -%s" % (ref, mode))
            if "success" not in response:
                return None
            self.keys.append(ref)
            return ref

    def del_key(self, ref):
        """
        Delete a key.

        (ref)
        Return None or LCDd response on error
        """
        if ref not in self.keys:
            response = self.request("client_del_key %s" % (ref))
            self.keys.remove(ref)
            if "success" in response:
                return None
            else:
                return response

    def output(self, value):
        """
        Sets the client's output (on, off, int)

        Sets the general purpose output on some display modules to this value.
        Use on to set all outputs to high state, and off to set all to low state.
        The meaning of the integer value depends on your specific device, usually
        it is a bit pattern describing the state of each output line.

        Return None or LCDd response on error
        """
        response = self.request(("output %s" % (value)).encode())
        if "success" in response:
            return None
        else:
            return response

    def get_server_info(self):
        """
        Returns information about the server and the connected
        LCD as a dictionary with the following keys:

            "server_version", "protocol_version",
            "screen_width", "screen_height",
            "cell_width", "cell_height"
        """
        return self.server_info
