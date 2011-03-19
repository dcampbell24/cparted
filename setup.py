import shutil
import os

from distutils.core import setup

try:
    shutil.copy('cparted.py', 'cparted')
except Exception:
    pass

setup(name='cparted',
      version='0.1',
      author='David Campbell',
      author_email='davekong@archlinux.us',
      url='https://github.com/davekong/cparted',
      description='Curses based disk partition manipulation program',
      long_description="""\
      cparted is a curses based disk partition manipulation program that aims
      to replace cfdisk by providing a friendly curses interface with the
      partition manipulation power of libparted. cparted is written in Python,
      and thus makes use of libparted through pyparted.""",
      classifiers=['Environment :: Console :: Curses',
                   'Intended Audience :: System Administrators',
                   'License :: OSI Approved :: GNU General Public License (GPL)',
                   'Natural Language :: English',
                   'Programming Language :: Python :: 2.7'],
      license='GPL',
      data_files=[('/usr/share/man/man8', ['cparted.8']),
                  ('/usr/share/doc/cparted', ['README.md'])],
      requires=['pyparted'],
      scripts=['cparted'])
