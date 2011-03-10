#!/usr/bin/env python2
"""
Copyright (C) 2011 David Campbell <davekong@archlinux.us>
This program is licensed under the GPL. See COPYING for the full license.

This program is a curses front end to pyparted that mimics cfdisk.
"""

import curses
import sys
import platform
from functools import reduce

import parted

__version__ = ""

help__=\
"""
Help Screen for cparted

This is cparted, a curses based disk partitioning program, which
allows you to create, delete and modify partitions on your hard
disk drive.

Copyright (C) 2011 David Campbell

Command      Meaning
-------      -------
  b          Toggle bootable flag of the current partition
  d          Delete the current partition
  h          Print this screen
  n          Create new partition from free space
  p          Print partition table to the screen or to a file
             There are several different formats for the partition
             that you can choose from:
                r - Raw data (exactly what would be written to disk)
                s - Table ordered by sectors
                t - Table in raw format
  q          Quit program without writing partition table
  u          Change units of the partition size display
             Rotates through MB, sectors and cylinders
  W          Write partition table to disk (must enter upper case W)
             Since this might destroy data on the disk, you must
             either confirm or deny the write by entering `yes' or
             `no'
Up Arrow     Move cursor to the previous partition
Down Arrow   Move cursor to the next partition
CTRL-L       Redraws the screen
  ?          Print this screen

Note: All of the commands can be entered with either upper or lower
case letters (except for Writes).
"""

PART_TABLE = 10 # Where to start listing partitions from.
PART_TYPES = ("Logical", "Extended", "Free Space", "Metadata", "Protected")
DEVICE_TYPES = ("Unknown", "SCSI", "IDE", "DAC960", "CPQ Array", "File",
                "ATA RAID", "I2O", "UBD", "DASD", "VIODASD", "SX8", "DM",
                "XVD", "SDMMC", "Virtual Block")

START = 0
END = 1

NAME = 0
FUNC = 1

class Menu(object):
    """Holds the state of the options menu and partition table, provides
       functions for drawing them, and contains the options functions."""

    def __init__(self, window, device):
        self.part_opts = (("Bootable", self.bootable), ("Delete", self.delete),
                          ("Help", self.help_), ("Print", self.print_),
                          ("Quit", self.quit), ("Units", self.units),
                          ("Write", self.write), ("New Table", self.new_table))
        self.free_opts = (("Help", self.help_), ("New", self.new),
                          ("Print", self.print_), ("Quit", self.quit),
                          ("Units", self.units), ("Write", self.write),
                          ("New Table", self.new_table))
        self.device = device
        self.disk = parted.Disk(device)
        self.partitions = minus_ext(get_partitions(self.disk))
        self.select_partition(0)
        self.window = window
        self.unit = "MB"

    @property
    def header(self):
        text=\
        """\
        cparted {:}

        Disk Drive: {:}
        Model: {:} ({:})
        Size: {:} sectors, {:.1f} GB
        Sector Size (logical/physical): {:}B/{:}B
        Partition Table: {:}
        """.format(__version__, self.device.path, self.device.model,
                   DEVICE_TYPES[self.device.type], self.device.length,
                   self.device.getSize("GB"),
                   self.device.sectorSize, self.device.physicalSectorSize,
                   self.disk.type)
        part_fields = ("Name", "Flags", "Part Type", "FS Type",
                       "Size({:})".format(self.unit))
        header = ""
        for line in text.splitlines():
            header += "{:^{:}}".format(line, self.window_width)
        header += self.format_fields(part_fields) + "\n"
        header += "-" * self.window_width + "\n"
        return header

    @property
    def window_lines(self):
        return self.window.getmaxyx()[0]

    @property
    def window_width(self):
        return self.window.getmaxyx()[1]

    @property
    def menu_line(self):
        return self.window_lines - 3

    def center(self, string):
        return (self.window_width // 2) - (len(string) // 2)

    @property
    def opts_offset(self):
        return self.center(self.opts_string)

    @property
    def opt_coords(self):
        coords = []
        for char, i in zip(self.opts_string, range(0, len(self.opts_string))):
            if char == "[":
                j = i
            if char == "]":
                coords.append((j + self.opts_offset, i - j + 1))
        return coords

    @property
    def opts_string(self):
        return "[" + "] [".join(zip(*self.vis_opts)[NAME]) + "]"

    def call(self, option):
        """Attempt to call an option specified by the correspond string."""
        names, funcs = zip(*self.vis_opts)
        if option == "Selected":
            return funcs[self.selected_option]()
        try:
            i = names.index(option)
            return funcs[i]()
        except ValueError:
            self.draw_info("%s is not a legal option for this partition." %
                           option)

    def select_partition(self, part):
        """Change the currently selected partition."""
        self.__partition_number = part
        self.__partition = self.partitions[part]
        self.selected_option = 1 # Delete/New
        if self.__partition.type & parted.PARTITION_FREESPACE:
            self.vis_opts = self.free_opts
        else:
            self.vis_opts = self.part_opts

    def draw_menu(self):
        self.draw_header()
        self.draw_partitions()
        self.draw_options()

    def refresh_menu(self):
        self.partitions = minus_ext(get_partitions(self.disk))

        if self.__partition_number >= len(self.partitions):
            self.chgat_partition(curses.A_NORMAL)
            self.select_partition(len(self.partitions) - 1)
        else:
            self.select_partition(self.__partition_number)

        self.window.move(PART_TABLE, 0)
        self.window.clrtobot()
        self.draw_partitions()
        self.draw_options()

    def draw_header(self):
        self.window.addstr(0, 0, self.header)

    def draw_info(self, string):
        """Add information line to the bottom of the main window"""
        self.window.hline(self.menu_line + 2, 0, " ", self.window_width)
        self.window.addstr(self.menu_line + 2, self.center(string), string)

    def draw_options(self):
        """Redraw the menu when switching partitions."""
        self.window.hline(self.menu_line, 0, " ", self.window_width)
        self.window.addstr(self.menu_line, self.opts_offset, self.opts_string)
        self.chgat_option(curses.A_STANDOUT)
        self.draw_info(self.vis_opts[self.selected_option][FUNC].__doc__)

    def format_fields(self, cols):
        fields = ("{:{a}} {:{a}} {:{a}} {:{a}} {:>{a}}").\
                  format(*cols, a = int(self.window_width / 5.5))
        return "{:^{:}}".format(fields, self.window_width - 1)

    def draw_partitions(self):
        s = ""
        for part in self.partitions:
            s += self.format_fields((part.getDeviceNodeName(),
                                     part.getFlagsAsString(),
                                     part_type(part), fs_type(part),
                                     int(part.getSize(self.unit)))) + "\n"
        self.window.addstr(PART_TABLE, 0, s)
        self.window.chgat(PART_TABLE + self.__partition_number, 0, curses.A_STANDOUT)

    def chgat_partition(self, attr):
        self.window.chgat(PART_TABLE + self.__partition_number, 0, attr)

    def up_down(self, key):
        if key == curses.KEY_UP:
            if self.__partition_number > 0:
                self.chgat_partition(curses.A_NORMAL)
                self.select_partition(self.__partition_number - 1)
                self.chgat_partition(curses.A_STANDOUT)
        elif self.__partition_number < (len(self.partitions) - 1):
            self.chgat_partition(curses.A_NORMAL)
            self.select_partition(self.__partition_number + 1)
            self.chgat_partition(curses.A_STANDOUT)
        self.draw_options()

    def chgat_option(self, attr):
        self.window.chgat(self.menu_line,
                          self.opt_coords[self.selected_option][START],
                          self.opt_coords[self.selected_option][END], attr)

    def left_right(self, key):
        num_opts = len(self.vis_opts)
        self.chgat_option(curses.A_NORMAL)

        if key == curses.KEY_LEFT:
            self.selected_option = (self.selected_option - 1) % num_opts
        else:
            self.selected_option = (self.selected_option + 1) % num_opts

        self.chgat_option(curses.A_STANDOUT)
        self.draw_info(self.vis_opts[self.selected_option][FUNC].__doc__)

    def sub_menu(self, opts):
        """Create a sub-menu, with limited input options, that captures the
           return value of the selected option."""
        self.vis_opts = opts
        self.selected_option = 0
        self.draw_options()
        while True:
            key = self.window.getch()
            if key == -1: # no input
                continue
            if key == curses.KEY_RESIZE or key == 12: #^L
                self.window.erase()
                self.draw_menu()
            if key == curses.KEY_RIGHT or key == curses.KEY_LEFT:
                self.left_right(key)
            if key == ord("\n"):
                return self.call("Selected")


    ###########################################################################
    ## Option menu functions
    ###########################################################################
    def bootable(self):
        """Toggle bootable flag of the current partition."""
        toggle_flag(self.__partition, parted.PARTITION_BOOT)
        self.draw_partitions()

    def delete(self):
        """Delete the current partition."""
        logical = self.__partition.type & parted.PARTITION_LOGICAL
        self.disk.deletePartition(self.__partition)
        if logical:
            self.disk.minimizeExtendedPartition()
        self.refresh_menu()

    def help_(self):
        """Print help screen."""
        help_win = curses.newwin(self.window_lines, self.window_width, 0, 0)
        help_win.overlay(self.window)
        info = "Press a key to continue."

        lines = help__.splitlines(True)
        while len(lines) > 0:
            s = reduce(lambda x, y: x + y, lines[:self.window_lines - 3])
            del lines[:self.window_lines - 3]
            help_win.erase()
            help_win.insstr(0, 0, s)
            help_win.addstr(self.window_lines - 1, self.center(info), info)
            help_win.getch()
        self.window.redrawwin()

    def print_(self):
        """Print partition table to the screen or to a file."""
        pass

    def quit(self):
        """Quit program without writing partition table."""
        sys.exit()

    def units(self):
        """Change the units used to specify and display partition size."""
        B = make_fn("B", "bytes")
        kB = make_fn("kB", "kilobytes")
        MB = make_fn("MB", "megabytes")
        GB = make_fn("GB", "gigabytes")
        KiB = make_fn("KiB", "kibibytes")
        MiB = make_fn("MiB", "mebibytes")
        GiB = make_fn("GiB", "gibibytes")
        sectors = make_fn("sectors", "For those full of awesome.")
        cancel = make_fn(None, "Don't chnage the units.")
        fs = (B, kB, MB, GB, KiB, MiB, GiB, sectors)
        u = self.sub_menu(tuple([(f(), f) for f in fs]) + (("Cancel", cancel),))
        if u:
            self.unit = u
            self.draw_header()
        self.refresh_menu()

    def write(self):
        """Write partition table to disk (this might destroy data)."""
        self.draw_info("Are you sure you want to write the partition table to disk? y/N")
        key = self.window.getkey()
        if key == "y" or key == "Y":
            self.draw_info("Writing changes to disk...")
            self.disk.commit()
        else:
            self.draw_info("Did not write changes to disk.")

    def new(self):
        """Create a new partition from free space."""
        def create_primary():
            """Create a new primary partition."""
            return parted.PARTITION_NORMAL

        def create_logical():
            """Create a new logical partition."""
            return parted.PARTITION_LOGICAL

        def cancel():
            """Don't create a partition."""
            self.vis_opts = self.free_opts
            self.draw_options()
            return None

        def at_beginning():
            """Add partition at beginning of free space."""
            return "Beginning"

        def at_end():
            """Add partiton at end of free space."""
            return "End"

        opts1 = (("Primary", create_primary), ("Logical", create_logical),
                 ("Cancel", cancel))
        opts2 = (("Beginning", at_beginning), ("End", at_end),
                 ("Cancel", cancel))

        alignment = self.device.optimumAlignment
        sector_size = self.device.sectorSize
        free = self.__partition.geometry
        start = free.start
        end = free.end
        length = None

        # Determine what type of partition to create.
        part_type = check_free_space(self.__partition)
        if part_type == "Pri/Log":
            part_type = self.sub_menu(opts1)
            if part_type is None:
                return
        elif part_type == "Primary":
            part_type = parted.PARTITION_NORMAL
        else:
            part_type = parted.PARTITION_LOGICAL

        # Determine what length the new partition should be.
        text = "Size in {:}: ".format(self.unit)
        offset = self.center(text + str(free.getSize(self.unit)))
        self.window.hline(self.menu_line, 0, " ", self.window_width)
        self.window.addstr(self.menu_line, offset, text + str(free.getSize(self.unit)))
        self.window.move(self.menu_line, offset + len(text))
        key = self.window.getkey()
        if key != "\n":
            self.window.clrtoeol()
            self.window.addstr(self.menu_line, offset + len(text), key)
            curses.echo()
            try:
                length = self.window.getstr(self.menu_line, offset + len(text) + 1)
                length = int(key + length)
                if self.unit != "sectors":
                    length = parted.bytesToSectors(length, self.unit, sector_size)
            except Exception as e:
                self.refresh_menu()
                self.draw_info("ERROR: {:}".format(e))
                return
            finally:
                curses.noecho()

        # Determine whether the partition should be placed at the beginning or end
        # of the free space, and adjust the start/end locations accordingly.
        if length and length < free.length:
            location = self.sub_menu(opts2)
            if location == "Beginning":
                end = start + length
            elif location == "End":
                start = end - length
            else:
                return

        try:
            # Make room for a logical partition's metadata and adjust the
            # extended partition as necessary.
            if part_type == parted.PARTITION_LOGICAL:
                start += alignment.grainSize
                grow_ext(self.__partition)

            if not alignment.isAligned(free, start):
                start = alignment.alignDown(free, start)
            if not alignment.isAligned(free, end):
                end = alignment.alignUp(free, end)

            free = parted.Geometry(self.device, start, end = end)
            max_length = self.disk.maxPartitionLength

            if max_length and max_length < free.length:
                self.draw_info("ERROR: partition size too large")
                return

            part = parted.Partition(self.disk, part_type, geometry = free)
            constraint = parted.Constraint(exactGeom = free)
            self.disk.addPartition(part, constraint)

        except Exception as e:
            if part_type == parted.PARTITION_LOGICAL:
                self.disk.minimizeExtendedPartition()
            self.refresh_menu()
            self.draw_info("ERROR: {:}".format(e))
            return

        if part_type == parted.PARTITION_LOGICAL:
            self.disk.minimizeExtendedPartition()
        self.refresh_menu()

    def new_table(self):
        """Create a new partition table on the device."""
        arch = platform.machine()
        cancel = make_fn(None, "Don't create a new disklabel (partition table).")
        fs = map(make_fn, parted.archLabels[arch])
        ty = self.sub_menu(tuple([(f(), f) for f in fs]) + (("Cancel", cancel),))
        if ty:
            self.disk = parted.freshDisk(self.device, ty)
        self.refresh_menu()

def make_fn(ret, doc=""):
    def fn():
        return ret
    fn.__doc__  = doc
    return fn

def get_partitions(disk):
    """Get all primary, logical, extended, and free space partitions."""
    partitions = disk.partitions
    free_space = disk.getFreeSpacePartitions()
    partitions = sorted(list(partitions) + free_space,
                        key = lambda ps: ps.geometry.start)
    return partitions

def toggle_flag(part, flag):
    if part.getFlag(flag):
        part.unsetFlag(flag)
    else:
        part.setFlag(flag)

def minus_ext(parts):
    return [p for p in parts if p != p.disk.getExtendedPartition()]

def grow_ext(part):
    """Grow, or create and grow, an extended partition to max size."""
    ext = part.disk.getExtendedPartition()
    if ext:
        c = parted.Constraint(device = part.disk.device)
        part.disk.maximizePartition(ext, c)
    else:
        c = parted.Constraint(exactGeom = part.geometry)
        p = parted.Partition(part.disk, parted.PARTITION_EXTENDED, geometry = part.geometry)
        part.disk.addPartition(p, c)


def part_type(part):
    if part.type & parted.PARTITION_FREESPACE:
        return check_free_space(part)
    elif part.type == parted.PARTITION_NORMAL:
        return "Primary"
    flags = []
    for flag, value in zip(bin(part.type)[::-1], PART_TYPES):
        if flag == "1":
            flags.append(value)
    return ", ".join(flags)

def fs_type(part):
    if part.fileSystem:
        return part.fileSystem.type
    elif part.type & parted.PARTITION_FREESPACE:
        return "Free Space"
    else:
        return ""

def check_free_space(part):
    """Check to see what the region of free space can be used for."""
    disk = part.disk
    if len(disk.partitions) == disk.maxSupportedPartitionCount:
        return "Unusable" # Too many partitions
    if disk.primaryPartitionCount == disk.maxPrimaryPartitionCount:
        if (len(disk.getLogicalPartitions()) == disk.getMaxLogicalPartitions):
            return "Unusable" # Too many logical partitions or no extended.
        elif next_to_extended(part):
            return "Logical"
        else:
            return "Unusable"
    elif not disk.getExtendedPartition():
        return "Pri/Log" # If logical, create an extended partition.
    elif next_to_extended(part):
        return "Pri/Log"
    else:
        return "Primary"

def next_to_extended(part):
    """True if next to or inside of the extended partition"""
    parts = get_partitions(part.disk)
    for p, i in zip(parts, range(len(parts))):
        if p.type & parted.PARTITION_EXTENDED:
            index = i
    if parts[index - 1] == part:
        return True
    x = 1
    if parts[index + x] == part:
        return True
    while parts[index + x].type & parted.PARTITION_LOGICAL:
        x += 1
        if parts[index + x] == part:
            return True
    return False

def start_curses(stdscr, device):
    # Allow capture of KEY_ENTER via '\n'.
    curses.nl()

    # Draw the header, partitions table, and options menu
    menu = Menu(stdscr, device)
    menu.draw_menu()

    # The main loop that captures user input.
    while True:
        key = stdscr.getch()
        if key == -1: # no input
            continue
        if key == curses.KEY_RESIZE or key == 12: #^L
            stdscr.erase()
            menu.draw_menu()
        if key == curses.KEY_DOWN or key == curses.KEY_UP:
            menu.up_down(key)
        if key == curses.KEY_RIGHT or key == curses.KEY_LEFT:
            menu.left_right(key)
        if key == ord("\n"):
            menu.call("Selected")
        if key == ord("b") or key ==  ord("B"):
            menu.call("Bootable")
        if key == ord("d") or key ==  ord("D"):
            menu.call("Delete")
        if key == ord("h") or key == ord("H") or key == ord("?"):
            menu.call("Help")
        if key == ord("n") or key == ord("N"):
            menu.call("New")
        if key == ord("p") or key == ord("P"):
            menu.call("Print")
        if key == ord("q") or key == ord("Q"):
            menu.call("Quit")
        if key == ord("u") or key == ord("U"):
            menu.call("Units")
        if key == ord("W"):
            menu.call("Write")

def main():
    try:
        device = parted.Device(sys.argv[1])
        parted.Disk(device).minimizeExtendedPartition()
    except IndexError:
        sys.stderr.write("ERROR: you must enter a device path\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)
    else:
        curses.wrapper(start_curses, device)

if __name__ == "__main__":
    main()
