#!/usr/bin/env python

from setuptools import setup

long_description = None
with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(name='heare-config',
      version='0.0.7',
      description='Heare.io Configuration Utilities',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Sean Fitzgerald',
      author_email='seanfitz@heare.io',
      url='https://github.com/heare-io/heare-config',
      packages=['heare.config'],
      setup_requires=['wheel']
      )
