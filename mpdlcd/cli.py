# -*- coding: utf-8 -*-
# Copyright (c) 2011-2012 Raphaël Barrois

from lcdproc import server as lcdproc_server

import logging
from logging import handlers as logging_handlers
import optparse
import socket
import time

from mpdlcd import lcdrunner
from mpdlcd import mpdwrapper


DEFAULT_MPD_PORT = 6600
DEFAULT_LCD_PORT = 13666
DEFAULT_LOGLEVEL = 'warning'
DEFAULT_SYSLOG_FACILITY = 'daemon'
DEFAULT_SYSLOG_ADDRESS = '/dev/log'
DEFAULT_LOGFILE = '-'  # For stdout
DEFAULT_RETRIES = 3
DEFAULT_RETRY_WAIT = 3


def _make_hostport(conn, default_host, default_port):
    if not conn:
        return default_host, default_port

    parts = conn.split(':', 1)
    host = parts[0]
    if len(parts) == 1:
        port = default_port
    else:
        port = parts[1]

    return host, int(port)

logger = logging.getLogger('mpdlcdd')

def _make_lcdproc(lcd_host, lcd_port, lcd_debug=False, retries=DEFAULT_RETRIES,
        retry_wait=DEFAULT_RETRY_WAIT):
    for _ in xrange(retries):
        try:
            return lcdproc_server.Server(lcd_host, lcd_port, debug=lcd_debug)
        except socket.error as e:
            logger.warning('Unable to connect to lcdproc server %s:%s: %s',
                lcd_host, lcd_port, e)
            time.sleep(retry_wait)
    logger.error('Unable to connect to lcdproc %s:%s after %d attempts.',
        lcd_host, lcd_port, retries)
    raise SystemExit(1)


def run_forever(lcdproc='', mpd='', lcd_debug=False, retries=DEFAULT_RETRIES,
        retry_wait=DEFAULT_RETRY_WAIT):
    lcd_host, lcd_port = _make_hostport(lcdproc, 'localhost', 13666)
    mpd_host, mpd_port = _make_hostport(mpd, 'localhost', 6600)

    lcd = _make_lcdproc(lcd_host, lcd_port, lcd_debug, retries, retry_wait)
    client = mpdwrapper.MPDClient(mpd_host, mpd_port)
    runner = lcdrunner.MpdRunner(client, lcd)

    client.connect()
    runner.run()


LOGLEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


def _make_parser():
    parser = optparse.OptionParser()

    # General options
    group = optparse.OptionGroup(parser, 'Connection')
    group.add_option('-l', '--lcdproc', dest='lcdproc',
            help='Connect to lcdproc at LCDPROC', metavar='LCDPROC')
    group.add_option('-m', '--mpd', dest='mpd',
            help='Connect to mpd running at MPD', metavar='MPD')
    group.add_option('--lcdproc-debug', dest='lcd_debug', action='store_true',
            help='Add full debug output for lcdproc', default=False)
    group.add_option('-r', '--retries', dest='retries', type='int',
            help='Retry connections RETRY times (default: %d)' %
                    DEFAULT_RETRIES,
            metavar='RETRY')
    group.add_option('-w', '--retry-wait', dest='retry_wait', type='float',
            help='Wait RETRY_WAIT between connection attempts (default: %.1fs)' %
                    DEFAULT_RETRY_WAIT,
            metavar='RETRY_WAIT')
    parser.add_option_group(group)

    # Logging options
    group = optparse.OptionGroup(parser, 'Logging')
    group.add_option('-s', '--syslog', dest='syslog', action='store_true',
            help='Enable syslog logging (default: False)', default=False)

    group.add_option('--syslog-facility', dest='syslog_facility',
            default=DEFAULT_SYSLOG_FACILITY,
            help='Log into syslog facility FACILITY (default: %s)' % 
                    DEFAULT_SYSLOG_FACILITY,
            metavar='FACILITY')

    group.add_option('--syslog-server', dest='syslog_server',
            default=DEFAULT_SYSLOG_ADDRESS,
            help='Log into syslog at SERVER (default: %s)' %
                    DEFAULT_SYSLOG_ADDRESS,
            metavar='SERVER')

    group.add_option('-f', '--logfile', dest='logfile',
            default=DEFAULT_LOGFILE,
            help="Log into LOGFILE ('-' for stderr)", metavar='LOGFILE')

    group.add_option('--loglevel', dest='loglevel', type='choice',
            help='Logging level (%s; default: %s)' %
                    ('/'.join(LOGLEVELS.keys()), DEFAULT_LOGLEVEL),
            choices=LOGLEVELS.keys(), default=DEFAULT_LOGLEVEL)

    parser.add_option_group(group)

    return parser


def _setup_logging(syslog=False, syslog_facility=DEFAULT_SYSLOG_FACILITY,
        syslog_server=DEFAULT_SYSLOG_ADDRESS, logfile=DEFAULT_LOGFILE,
        loglevel=DEFAULT_LOGLEVEL, **kwargs):
    level = LOGLEVELS[loglevel]

    verbose_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s')
    quiet_formatter = logging.Formatter(
            '%(levelname)s %(name)s %(message)s')

    if syslog:
        if syslog_server and syslog_server[0] == '/':
            address = syslog_server
        else:
            address = _make_hostport(syslog_server, 'localhost', logging.SYSLOG_UDP_PORT)
        handler = logging_handlers.SysLogHandler(address, facility=syslog_facility)
        handler.setFormatter(quiet_formatter)

    elif logfile == '-':
        handler = logging.StreamHandler()
        handler.setFormatter(quiet_formatter)

    else:
        handler = logging_handlers.FileHandler(logfile, level=level)
        handler.setFormatter(verbose_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def _extract_options(options, *args, **kwargs):
    extract = {}
    for key in args:
        extract[key] = getattr(options, key)
    for key, default in kwargs:
        extract[key] = getattr(options, key, default)
    return extract


def main(argv):
    parser = _make_parser()
    options, args = parser.parse_args(argv)
    _setup_logging(**_extract_options(options,
        'syslog', 'syslog_facility', 'syslog_server', 'logfile', 'loglevel'))
    run_forever(**_extract_options(options,
        'lcdproc', 'mpd', 'lcd_debug', 'retries', 'retry_wait'))