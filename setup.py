#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

from setuptools import setup


setup(name='fotc',
      version='0.1',
      description='A telegram bot with misc utilities for groups',
      url='http://github.com/hstefan/fotc',
      author='Stefan Puhlmann',
      author_email='hugopuhlmann@gmail.com',
      license='MIT',
      packages=['fotc'],
      entry_points={
          'console_scripts': ['fotc-bot = fotc.main:main']
      },
      zip_safe=False)