#!/usr/bin/env python

from distutils.core import setup
from subprocess import Popen, PIPE
import errno
import msrx

# All of this so we don't have to maintain an RST version of README.md
# for when submitting packages to PyPi - arghh

readme_path = 'README.md'

try:
  
  readme = Popen(
    ['pandoc', '-f', 'markdown', '-t', 'rst', readme_path, '-o', '-'],
    stdout=PIPE
  ).communicate()[0].decode('utf8')
  if not readme:
    raise Exception()
  
except:

  print('warning: pandoc coud not be used to convert readme to RST')
  readme = open(readme_path, 'rb').read().decode('utf8')

setup(
  name='msrx',
  version=msrx.__version__,
  packages=['msrx'],
  scripts=['scripts/msrx'],
  install_requires=['PySerial'],

  author=msrx.__author__,
  author_email=msrx.__email__,
  maintainer=msrx.__maintainer__,
  maintainer_email=msrx.__email__,
  description=msrx.__description__,
  long_description=readme,
  license=msrx.__license__,
  url='https://github.com/oxplot/msrx',

  classifiers=[
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Natural Language :: English',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.9',
    'Operating System :: POSIX :: Linux',
    'Topic :: Utilities'
  ]
)
