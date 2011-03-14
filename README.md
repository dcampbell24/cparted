cparted
========

Copyright (C) 2011 David Campbell <davekong@archlinux.us>
This program is licensed under the GPL. See COPYING for the full license.

This program is a curses front end to [pyparted][1] that mimics cfdisk. It
has not been widely tested, and has known issues with creating gaps between
partitions, and sometimes corrupting a partition table. It is only suggested
for testing at the moment.

[1]: http://git.fedorahosted.org/git/?p=pyparted.git

BUGS
----
When creating primary partitions, there tend to be gaps of free
space between the partitions that are not usable. These gaps are typically
just smaller than the optimal alignment grain size of the HDD (or SSD). These
gaps may be hidden in a future release, but are left visible for now as the
author does not know if there is a proper way to get rid of them.

If the user creates a logical partition on a disk without any primary
partitions, two regions of free space may appear next to each other, and
writing to disk may corrupt the partition table. Creating a logical partition
without any primary partitions is allowed at this point, despite the known
issue, for testing reasons, and because there is no reason a user should not
be able to have a msdos partition table without primary partitions.

HACKING
-------
If you wish to contribute to [cparted][2], please fork it on github, and then make
pull requests. Your code should follow the guidelines of [PEP 8][3].

[2]: https://github.com/davekong/cparted
[3]: http://www.python.org/dev/peps/pep-0008/
