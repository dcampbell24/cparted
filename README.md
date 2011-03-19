cparted
========

Copyright (C) 2011 David Campbell <davekong@archlinux.us>
This program is licensed under the GPL. See COPYING for the full license.

This program is a curses front end to [pyparted][1] that mimics cfdisk. It
has not been widely tested, and has known issues with creating gaps between
partitions, and sometimes corrupting a partition table. It is only suggested
for testing at the moment.

[1]: http://git.fedorahosted.org/git/?p=pyparted.git

WARNING
-------
Sometimes, when adding a logical partition, two regions of free space will
appear next to each other. This is bad. Do not write to disk if this happens.
If you do, the partition table will probably be corrupted, and you will have
to create a new one. One sure way to trigger this bug seems to be creating a
logical partition on a disk without any primary partitions.

HACKING
-------
If you wish to contribute to [cparted][2], please fork it on github, and then make
pull requests. Your code should follow the guidelines of [PEP 8][3].

[2]: https://github.com/davekong/cparted
[3]: http://www.python.org/dev/peps/pep-0008/
