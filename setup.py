import shutil
import os

from distutils.core import setup

try:
    shutil.copy('cparted.py', 'cparted')

    setup(name='cparted',
          version='0.1dev',
          author='David Campbell',
          author_email='davekong@archlinux.us',
          url='https://github.com/davekong/cparted',
          description='Curses based disk partition manipulation program',
          classifiers=[
              'Environment :: Console :: Curses',
              'Intended Audience :: System Administrators',
              'License :: OSI Approved :: GNU General Public License (GPL)',
              'Natural Language :: English',
              'Programming Language :: Python :: 2.7',
          ],
          data_files=[('/usr/share/man/man8', ['cparted.8']),
                      ('/usr/share/doc/cparted', ['README.md'])
                     ],
          requires=['pyparted'],
          scripts=['cparted'],
         )
finally:
    os.remove('cparted')
