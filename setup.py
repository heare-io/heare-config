#!/usr/bin/env python

from distutils.core import setup
import os
from typing import Optional

long_description: Optional[str] = None
if os.path.exists('README.md'):
    long_description = open('README.md', 'r').read()

setup(name='heare-config',
      version='0.0.6',
      description='Heare.io Configuration Utilities',
      long_description=str(long_description),
      author='Sean Fitzgerald',
      author_email='seanfitz@heare.io',
      url='https://github.com/heare-io/heare-config',
      packages=['heare.config'],
      )
