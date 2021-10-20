# msrx.py - Library for talking with MSR605 magnetic card reader/writer
# Copyright (C) 2014  Mansour Behabadi <mansour@oxplot.com>
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

"""Library for talking with MSR605 magnetic card reader/writer"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import codecs
import os
import re
import sys

try:
  unicode = unicode
  range = xrange
  to_byte = chr
  to_uni = unichr
  input = raw_input
  biter = lambda x: x
except NameError:
  unicode = str
  to_byte = lambda c: bytes([c])
  to_uni = chr
  biter = lambda x: (to_byte(i) for i in x)

__author__ = 'Mansour Behabadi'
__copyright__ = 'Copyright (C) 2014 Mansour Behabadi'
__credits__ = ['Mansour Behabadi']
__email__ = 'mansour@oxplot.com'
__license__ = 'GPLv3'
__maintainer__ = 'Mansour Behabadi'
__version__ = '0.2'
__description__ = 'Library and command line utils to use MSR605 magnetic card reader/writer'
__progname__ = 'msrx'
__verinfo__ = """%s version %s
%s
This program is free software; you may redistribute it under the terms of the GNU General Public License version 3 or (at your options) any later version.
This program comes with absolutely no warranty.""" % (
  __progname__, __version__, __copyright__
)

_TRACK_CNT = 3
_DEF_DEV = '/dev/ttyUSB0'
_DEV_ENV = 'MSRX_DEV'
_DELIM = '|'
_DEF_TYPE = 'iso'

class ISO7811(object):

  _PARAM_MAP = {1: (0x20, 7), 2: (0x30, 5), 3: (0x30, 5)}
  _CODEC_NAMES = set(['iso7811_t%d' % i for i in _PARAM_MAP])

  @classmethod
  def codec_search(cls, name):
    if name in cls._CODEC_NAMES:
      andlen = lambda x: (x, len(x))
      params = cls._PARAM_MAP[int(name[-1])]
      return (
        (lambda data: andlen(''.join(cls._enc(data, *params)))),
        (lambda data: andlen(b''.join(cls._dec(data, *params)))),
        None,
        None
      )
    return None
  
  @classmethod
  def _dec(cls, data, low, bits):
    atbit, whole = 0, 0
    for d in data:
      part = (ord(d) - low) & ((1 << (bits - 1)) - 1)
      part |= (~(((part * 0x0101010101010101)
              & 0x8040201008040201) % 0x1FF) & 1) << (bits - 1)
      whole |= (part << atbit) & 255
      atbit += bits
      if atbit > 7:
        yield to_byte(whole)
        atbit = atbit % 8
        whole = part >> (bits - atbit)
    if atbit > 0:
      yield to_byte(whole)

  @classmethod
  def _enc(cls, data, low, bits):
    data = biter(iter(data))
    try:
      atbit, whole = 0, ord(next(data))
      while True:
        part = (whole >> atbit) & ((1 << bits) - 1)
        atbit += bits
        if atbit > 7:
          whole = ord(next(data))
          atbit = atbit % 8
          part |= (whole & ((1 << atbit) - 1)) << (bits - atbit)
        if part == 0:
          return
        # TODO verify the parity bit before yielding
        yield to_uni((part & ((1 << (bits - 1)) - 1)) + low)
    except StopIteration:
      pass

codecs.register(ISO7811.codec_search)

class ProtocolError(Exception):
  pass

class DeviceError(Exception):

  RW = 'read_write'
  CMD = 'command'
  SWP = 'swipe'
  ERASE = 'erase'

  def __init__(self, code):
    super(DeviceError, self).__init__('MSR605 %s error' % code)
    self.code = code

class MSRX(object):

  _DEV_ERR = {
    b'1': DeviceError.RW,
    b'2': DeviceError.CMD,
    b'4': DeviceError.CMD,
    b'9': DeviceError.SWP,
    b'A': DeviceError.ERASE
  }

  def __init__(self, device):
    '''Open the serial device'''
    import serial
    self._dev = serial.Serial(device, 9600, 8, serial.PARITY_NONE)

  def _send(self, d):
    self._dev.write(d)
    self._dev.flush()

  def _expect(self, d):
    rd = self._dev.read(len(d))
    if rd != d:
      raise ProtocolError('expected %s, got %s' % (
        codecs.encode(rd, 'hex_codec'), codecs.encode(d, 'hex_encode')
      ))

  def reset(self):
    '''Reset device to initial state'''
    self._send(b'\x1ba')

  def erase(self, tracks=(True, True, True)):
    '''Erase tracks

    tracks: tuple of 3 bools - each indicating whether the corresponding
            track should be erased.
    '''
    self._send(b'\x1bc' + to_byte(
      (1 if tracks[0] else 0)
      | (2 if tracks[1] else 0)
      | (4 if tracks[2] else 0)
    ))
    self._handle_status()

  def read(self):
    '''read() -> (t1, t2, t3)

    Read all tracks
    '''
    tracks = [b''] * _TRACK_CNT
    self._send(b'\x1bm')
    self._expect(b'\x1bs')
    for t in range(_TRACK_CNT):
      self._expect(b'\x1b' + to_byte(t + 1))
      tracks[t] = b''.join(
        # Some bit hackery to reverse the bits - we shouldn't need this
        # but the hardware works in mysterious ways.
        to_byte((((ord(c) * 0x80200802)
                & 0x0884422110) * 0x0101010101 >> 32) & 255)
        for c in biter(self._dev.read(ord(self._dev.read(1))))
      )
    self._expect(b'?\x1c')
    self._handle_status()
    return tracks

  def write(self, tracks):
    '''Write all tracks

    tracks: tuple of three byte strings, each data for the corresponding
            track. To preserve a track, pass empty byte string.
    '''
    self._send(b'\x1bn\x1bs')
    for t, i in zip(tracks, range(_TRACK_CNT)):
      self._send(b'\x1b' + to_byte(i + 1) + to_byte(len(t)) + t)
    self._send(b'?\x1c')
    self._handle_status()

  def _handle_status(self):
    self._expect(b'\x1b')
    status = self._dev.read(1)
    if status == b'0':
      return
    elif status in self._DEV_ERR:
      raise DeviceError(self._DEV_ERR[status])
    else:
      raise ProtocolError(
        "invalid status %s" % codec.encode(status, 'hex_codec')
      )

_DATA_CONV = {
  ('raw', 'hex'):
    (lambda d, _: codecs.encode(d, 'hex_codec')),
  ('hex', 'raw'): (lambda d, _: codecs.decode(d, 'hex_codec')),
  ('raw', 'iso'):
    (lambda d, t: codecs.encode(d, 'iso7811_t%d' % t)),
  ('iso', 'raw'): (lambda d, t: codecs.decode(d, 'iso7811_t%d' % t))
}

_DTYPE_VFY = {
  'hex': lambda d, _: bool(re.search(r'^[0-9a-fA-F]*$', d)),
  'iso': lambda d, t: bool(
    re.search(r'^[ -_]*$' if t == 1 else r'^[0-?]*$', d)
  )
}

def _do_read(args):

  print(_DELIM.join(
    _DATA_CONV[('raw', args.type)](d, t + 1)
    for d, t in zip(args.msrx.read(), range(_TRACK_CNT))
  ))

def _do_write(args):

  data = (args.data or input()).split(_DELIM)
  if len(data) != _TRACK_CNT:
    args.parser.error(
      "there must be exactly be %d '%s'"
      " in data separating the %d tracks"
      % (_TRACK_CNT - 1, _DELIM, _TRACK_CNT)
    )
  if not all(
    _DTYPE_VFY[args.type](d, t + 1)
    for d, t in zip(data, range(_TRACK_CNT))
  ):
    args.parser.error(
      "the data doesn't match the type given (%s)" % args.type
    )

  data = [
    _DATA_CONV[args.type, 'raw'](d, t + 1)
    for d, t in zip(data, range(_TRACK_CNT))
  ]
  args.msrx.write(data)

def _do_erase(args):

  args.msrx.erase(args.tracks)

def main():

  def track_sel_type(data):
    tracks = [False] * _TRACK_CNT
    try:
      for t in map(int, data.split(',')):
        if t > _TRACK_CNT or t < 1:
          raise argparse.ArgumentTypeError(
            'track numbers must be between %d and %d'
            % (1, _TRACK_CNT)
          )
        tracks[t - 1] = True
    except ValueError:
      raise argparse.ArgumentTypeError(
        'provide track numbers separated with commas - e.g 1,3'
      )
    return tracks

  def add_type_arg(parser):
    parser.add_argument(
      '-t', '--type',
      metavar='TYPE',
      default=_DEF_TYPE,
      choices=list(_DTYPE_VFY),
      type=unicode,
      help='data type: %s - defaults to %s'
           % (', '.join(_DTYPE_VFY), _DEF_TYPE)
    )

  if any(a == '--version' for a in sys.argv[1:]):
    print(__verinfo__)
    exit(0)

  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=__description__
  )
  parser.add_argument(
    '-D', '--dev',
    metavar='DEV',
    default=os.environ.get(_DEV_ENV, _DEF_DEV),
    help='serial device to use - can be override by %s env'
         ' variable - defaults to %s' % (_DEV_ENV, _DEF_DEV)
  )
  parser.add_argument(
    '-R', '--no-reset',
    action='store_true',
    default=False,
    help='do NOT issue reset before the main command'
  )
  parser.add_argument(
    '--version',
    action='store_true',
    help='show license and version of ' + __progname__
  )

  subparsers = parser.add_subparsers(
    dest='cmd'
  )

  parser_a = subparsers.add_parser(
    'read',
    description='Read card and output data as'
                " '%s' delimited string to stdout" % _DELIM,
    help='read card'
  )
  add_type_arg(parser_a)
  parser_a.set_defaults(func=_do_read)

  parser_a = subparsers.add_parser(
    'write',
    description="Write to card from '%s' delimited data in stdin"
                " or from --data command line arg" % _DELIM,
    help='write card'
  )
  parser_a.add_argument(
    '-d', '--data',
    metavar='DATA',
    default=None,
    type=unicode,
    help='data to write - overrides stdin'
  )
  add_type_arg(parser_a)
  parser_a.set_defaults(func=_do_write)

  parser_a = subparsers.add_parser(
    'erase',
    description='Erase all tracks',
    help='erase card'
  )
  parser_a.add_argument(
    '-t', '--tracks',
    metavar='TRACKS',
    default=','.join(str(i + 1) for i in range(_TRACK_CNT)),
    type=track_sel_type,
    help='tracks to erase - default is '
         + ','.join(str(i + 1) for i in range(_TRACK_CNT))
  )
  parser_a.set_defaults(func=_do_erase)

  args = parser.parse_args()
  args.parser = parser

  try:
    msrxinst = MSRX(args.dev)
    if not args.no_reset:
      msrxinst.reset()
    args.msrx = msrxinst
    args.func(args)
  except OSError as e:
    print(
      '%s: error: %s' % (__progname__, os.strerror(e.errno)),
      file=sys.stderr
    )
  except (DeviceError, ProtocolError) as e:
    print('%s: error: %s' % (__progname__, e.args[0]), file=sys.stderr)
    exit(254)
  except KeyboardInterrupt:
    print('keyboard interrupt', file=sys.stderr)
    exit(255)
