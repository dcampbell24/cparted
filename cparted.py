#!/usr/bin/env python2
"""
Copyright (C) 2011 David Campbell <davekong@archlinux.us>
This program is licensed under the GPL. See COPYING for the full license.

This program is a curses front end to pyparted that mimics cfdisk.
"""

import curses
import sys

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
  g          Change cylinders, heads, sectors-per-track parameters
             WARNING: This option should only be used by people who
             know what they are doing.
  h          Print this screen
  m          Maximize disk usage of the current partition
             Note: This may make the partition incompatible with
             DOS, OS/2, ...
  n          Create new partition from free space
  p          Print partition table to the screen or to a file
             There are several different formats for the partition
             that you can choose from:
                r - Raw data (exactly what would be written to disk)
                s - Table ordered by sectors
                t - Table in raw format
  q          Quit program without writing partition table
  t          Change the filesystem type
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
                          ("Help", self.help_), ("Maximize", self.maximize),
                          ("Print", self.print_), ("Quit", self.quit),
                          ("Type", self.type_), ("Units", self.units),
                          ("Write", self.write))
        self.free_opts = (("Help", self.help_), ("New", self.new),
                          ("Print", self.print_), ("Quit", self.quit),
                          ("Units", self.units), ("Write", self.write),
                          ("New Table", self.new_table))
        self.disk = parted.Disk(device)
        self.partitions = get_partitions(self.disk)
        self.select_partition(0)
        self.window = window

    @property
    def window_lines(self):
        return self.window.getmaxyx()[0]

    @property
    def window_width(self):
        return self.window.getmaxyx()[1]

    @property
    def menu_line(self):
        return self.window_lines - 3

    @property
    def offset(self):
        return (self.window_width // 2) - (len(self.options_string) // 2)

    @property
    def opt_coords(self):
        coords = []
        for char, i in zip(self.options_string,
                           range(0, len(self.options_string))):
            if char == "[":
                j = i
            if char == "]":
                coords.append((j + self.offset, i - j + 1))
        return coords

    @property
    def options_string(self):
        return "[" + "] [".join(zip(*self.vis_options)[NAME]) + "]"

    def call(self, option):
        """Attempt to call an option specified by the correspond string."""
        names, funcs = zip(*self.vis_options)
        if option == "Selected":
            funcs[self.selected_option]()
            return
        try:
            i = names.index(option)
            funcs[i]()
        except ValueError:
            self.draw_info("%s is not a legal option for this partition." %
                           option)

    def select_partition(self, part):
        """Change the currently selected partition."""
        self.__partition_number = part
        self.__partition = self.partitions[part]
        self.selected_option = 1 # Delete/New
        if self.__partition.type & parted.PARTITION_FREESPACE:
            self.vis_options = self.free_opts
        else:
            self.vis_options = self.part_opts

    def draw_info(self, string):
        """Add information line to the bottom of the main window"""
        self.window.hline(self.menu_line + 2, 0, " ", self.window_width)
        addstr_centered(self.window, self.window_width, self.menu_line + 2,
                        string)

    def draw_options(self):
        """Redraw the menu when switching partitions."""
        self.window.hline(self.menu_line, 0, " ", self.window_width)
        self.window.addstr(self.menu_line, self.offset, self.options_string)
        self.chgat_option(curses.A_STANDOUT)
        self.draw_info(self.vis_options[self.selected_option][FUNC].__doc__)

    def draw_partitions(self):
        s = ""
        for part in self.partitions:
            s += format_fields(self.window_width,
                               (part.getDeviceNodeName(),
                                part.getFlagsAsString(),
                                part_type(part), fs_type(part),
                                int(part.getSize('b') / 10**6))) + "\n"
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

    def chgat_option(self, attr):
        self.window.chgat(self.menu_line,
                          self.opt_coords[self.selected_option][START],
                          self.opt_coords[self.selected_option][END], attr)

    def left_right(self, key):
        if key == curses.KEY_LEFT:
            if self.selected_option > 0:
                self.chgat_option(curses.A_NORMAL)
                self.selected_option -= 1
                self.chgat_option(curses.A_STANDOUT)
        elif self.selected_option < (len(self.vis_options) - 1):
            self.chgat_option(curses.A_NORMAL)
            self.selected_option += 1
            self.chgat_option(curses.A_STANDOUT)
        self.draw_info(self.vis_options[self.selected_option][FUNC].__doc__)

    ###########################################################################
    ## Option menu functions
    ###########################################################################
    def bootable(self):
        """Toggle bootable flag of the current partition."""
        pass

    def delete(self):
        """Delete the current partition."""
        logical = self.__partition.type & parted.PARTITION_LOGICAL
        self.disk.deletePartition(self.__partition)
        if logical:
            self.disk.minimizeExtendedPartition()
        self.partitions = get_partitions(self.disk)
        self.select_partition(0)
        self.window.move(PART_TABLE, 0)
        self.window.clrtobot()
        self.draw_partitions()
        self.draw_options()

    def help_(self):
        """Print help screen."""
        help_win = curses.newwin(0, 0)
        help_win.overlay(self.window)

        lines = help__.splitlines(True)
        while len(lines) > 0:
            s = reduce(lambda x, y: x + y, lines[:self.window_lines - 3])
            del lines[:self.window_lines - 3]
            help_win.erase()
            help_win.insstr(0, 0, s)
            addstr_centered(help_win, self.window_width, self.window_lines - 1,
                            "Press a key to continue.")
            help_win.getch()
        self.window.redrawwin()

    def maximize(self):
        """Maximize disk usage of the current partition (experts only)."""
        pass

    def print_(self):
        """Print partition table to the screen or to a file."""
        pass

    def quit(self):
        """Quit program without writing partition table."""
        sys.exit()

    def type_(self):
        """Change the filesystem type (DOS, Linux, OS/2 and so on)."""
        pass

    def units(self):
        """Change units of the partition size display (MB, sect, cyl)."""
        pass

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
        # Menu: [Primary] [Logical] [Cancel] (if there is a choice)
        # Size: (defaults to max allowable aligned size)
        # Menu: [Beginning] [End] (if smaller than max size)
        pass

    def new_table(self):
        """Create a new partition table on the device (GPT, msdos)"""
        pass

def get_partitions(disk):
    """Return a list of all the partitions on a disk, including partitions
    represented by free space, sorted by there starting points."""
    partitions = disk.partitions
    free_space = disk.getFreeSpacePartitions()
    partitions = sorted(list(partitions) + free_space,
                        key = lambda ps: ps.geometry.start)
    return partitions

def part_type(part):
    if part.type & parted.PARTITION_FREESPACE:
        return check_free_space(part)
    elif part.type == 0:
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

def addstr_centered(window, width, line, string):
    """Add a string to the center of a window."""
    offset = (width // 2) - (len(string) // 2)
    window.addstr(line, offset, string)

def format_fields(window_width, cols):
    fields = ("{:{a}} {:{a}} {:{a}} {:{a}} {:>{a}}").\
              format(*cols, a = int(window_width / 5.5))
    return "{:^{:}}".format(fields, window_width - 1)

def header(device, window_width):
    text=\
    """\
    cparted {:}

    Disk Drive: {:}
    Model: {:} ({:})
    Size: {:} sectors, {:.1f} GB
    Sector Size (logical/physical): {:}B/{:}B
    Partition Table: {:}
    """.format(__version__, device.path, device.model,
               DEVICE_TYPES[device.type], device.length,
               device.getSize('b') / (10 ** 9), device.sectorSize,
               device.physicalSectorSize, parted.Disk(device).type)
    ret = ""
    for line in text.splitlines():
        ret += "{:^{:}}".format(line, window_width)
    ret += format_fields(window_width, ("Name", "Flags", "Part Type",
                                        "FS Type", "Size(MB)")) + "\n"
    ret += "-" * window_width + "\n"
    return ret

def start_curses(stdscr, device):
    # Allow capture of KEY_ENTER via '\n'.
    curses.nl()

    # Draw the header, partitions table, and options menu
    stdscr.addstr(header(device, stdscr.getmaxyx()[1]))
    menu = Menu(stdscr, device)
    menu.draw_partitions()
    menu.draw_options()

    # The main loop that captures user input.
    while True:
        key = stdscr.getch()
        if key == -1: # no input
            continue
        if key == curses.KEY_RESIZE or key == 12: #^L
            stdscr.erase()
            stdscr.addstr(0, 0, header(device, stdscr.getmaxyx()[1]))
            menu.draw_partitions()
            menu.draw_options()
        if key == curses.KEY_DOWN or key == curses.KEY_UP:
            menu.up_down(key)
            menu.draw_options()
        if key == curses.KEY_RIGHT or key == curses.KEY_LEFT:
            menu.left_right(key)
        if key == ord("\n"):
            menu.call("Selected")
        if key == ord("b") or key ==  ord("B"):
            menu.call("Bootable")
        if key == ord("d") or key ==  ord("D"):
            menu.call("Delete")
        if key == ord("g") or key ==  ord("G"):
            menu.call("Unknown")
        if key == ord("h") or key == ord("H") or key == ord("?"):
            menu.call("Help")
        if key == ord("m") or key == ord("M"):
            menu.call("Maximize")
        if key == ord("n") or key == ord("N"):
            menu.call("New")
        if key == ord("p") or key == ord("P"):
            menu.call("Print")
        if key == ord("q") or key == ord("Q"):
            menu.call("Quit")
        if key == ord("t") or key == ord("T"):
            menu.call("Type")
        if key == ord("u") or key == ord("U"):
            menu.call("Units")
        if key == ord("W"):
            menu.call("Write")

def main():
    try:
        device = parted.Device(sys.argv[1])
    except IndexError:
        sys.stderr.write("ERROR: you must enter a device path\n")
        sys.exit(1)
    except Exception, e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)
    else:
        curses.wrapper(start_curses, device)

if __name__ == "__main__":
    main()
