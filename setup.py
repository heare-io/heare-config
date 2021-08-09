#!/usr/bin/env python

from distutils.core import setup
import os
from typing import Optional

long_description = None
with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(name='heare-config',
      version='0.0.6',
      description='Heare.io Configuration Utilities',
      long_description=long_description,
      author='Sean Fitzgerald',
      author_email='seanfitz@heare.io',
      url='https://github.com/heare-io/heare-config',
      packages=['heare.config'],
      )
