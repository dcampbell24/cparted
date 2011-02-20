#!/usr/bin/env python2
"""
Copyright (C) 2011 David Campbell <davekong@archlinux.us>
This program is licensed under the GPL. See COPYING for the full license.

This program is a curses front end to pyparted that mimics cfdisk.
"""

import curses
import sys
from functools import partial
from math import ceil

import parted
import _ped

PART_TABLE = 9 # Where to start listing partitions from.
PART_TYPES = ("Logical", "Extended", "Free Space", "Metadata", "Protected")

START = 0
END = 1

NAME = 0
FUNC = 1

class OptMenu:
    """Holds the state of the options menu, provides functions for drawing it,
    and contains the options functions"""

    def __init__(self, window, partition):
        self.part_opts = ([("Bootable", self.bootable), ("Delete", self.delete),
                           ("Help", self.help_), ("Maximixe", self.maximize),
                           ("Print", self.print_), ("Quit", self.quit),
                           ("Type", self.type_), ("Units", self.units),
                           ("Write", self.write)])
        self.free_opts = ([("Help", self.help_), ("New", self.new),
                           ("Print", self.print_), ("Quit", self.quit),
                           ("Units", self.units), ("Write", self.write),
                           ("New Table", self.new_table)])
        self.partition(partition)
        self.window = window
        max_yx = window.getmaxyx()
        self.window_width = max_yx[1]
        self.menu_line = max_yx[0] - 3
        self.selected_option = 1 # Delete/New
        self.draw_menu()

    def __str__(self):
        options = []
        for opt in self.vis_options:
            options.append(opt[NAME])
        return "[" + "]  [".join(options) + "]"

    def partition(self, part):
        self.__partition = part
        if not part_type(part).find("Free Space") == -1:
            self.vis_options = self.free_opts
        else:
            self.vis_options = self.part_opts

    def offset(self):
        return int(ceil(self.window_width / 2.0) - ceil(len(str(self)) / 2.0))

    def opt_coords(self):
        coords = []
        for char, i in zip(str(self), xrange(0, len(str(self)))):
            if char == "[":
                j = i
            if char == "]":
                coords.append((j + self.offset(), i - j + 1))
        return coords

    def draw_menu(self):
        """Redraw the menu when switching partitions."""
        self.window.hline(self.menu_line, 0, " ", self.window_width)
        self.window.addstr(self.menu_line, self.offset(), str(self))
        self.chgat_selected(curses.A_STANDOUT)
        self.window.hline(self.menu_line + 2, 0, " ", self.window_width)
        addstr_centered(self.window, self.window_width, self.menu_line + 2,
                        self.vis_options[self.selected_option][FUNC].__doc__)

    def chgat_selected(self, attr):
        self.window.chgat(self.menu_line,
                          self.opt_coords()[self.selected_option][START],
                          self.opt_coords()[self.selected_option][END], attr)

    def left_right(self, key):
        if key == "KEY_LEFT":
            if self.selected_option > 0:
                self.chgat_selected(curses.A_NORMAL)
                self.selected_option -= 1
                self.chgat_selected(curses.A_STANDOUT)
        elif self.selected_option < (len(self.vis_options) - 1):
            self.chgat_selected(curses.A_NORMAL)
            self.selected_option += 1
            self.chgat_selected(curses.A_STANDOUT)
        self.window.hline(self.menu_line + 2, 0, " ", self.window_width)
        addstr_centered(self.window, self.window_width, self.menu_line + 2,
                        self.vis_options[self.selected_option][FUNC].__doc__)

    def bootable(self):
        """Toggle bootable flag of the current partition."""
        pass

    def delete(self):
        """Delete the current partition."""
        pass

    def help_(self):
        """Print help screen."""
        pass

    def maximize(self):
        """Maximize disk usage of the current partition (experts only)."""
        pass

    def print_(self):
        """Print partition table to the screen or to a file."""
        pass

    def quit(self):
        """Quit program without writing partition table."""
        pass

    def type_(self):
        """Change the filesystem type (DOS, Linux, OS/2 and so on)."""
        pass

    def units(self):
        """Change units of the partition size display (MB, sect, cyl)."""
        pass

    def write(self):
        """Write partition table to disk (this might destroy data)."""
        pass

    def new(self):
        """Create a new partition from free space."""
        pass

    def new_table(self):
        """Create a new partition table on the device (GPT, msdos)"""
        pass



def part_type(part):
    if part.type == 0:
        return "Primary"
    flags = []
    for flag, value in zip(bin(part.type)[::-1], PART_TYPES):
        if flag == "1":
            flags.append(value)
    return ", ".join(flags)

def fs_type(part):
    try:
        return part.fileSystem.type
    except AttributeError:
        return ""

def flags(part):
    if part.active:
        return part.getFlagsAsString()
    return ""

def nodeName(part):
    if part.active:
        return part.getDeviceNodeName()
    return ""


def up_down(window, key, high_part, part_count):
    if key == "KEY_UP":
        if high_part > 0:
            window.chgat(PART_TABLE + high_part, 0, curses.A_NORMAL)
            high_part -= 1
            window.chgat(PART_TABLE + high_part, 0, curses.A_STANDOUT)
    elif high_part < (part_count - 1):
        window.chgat(PART_TABLE + high_part, 0, curses.A_NORMAL)
        high_part += 1
        window.chgat(PART_TABLE + high_part, 0, curses.A_STANDOUT)
    return high_part

def addstr_centered(window, width, line, string):
    center = int(ceil(width / 2.0) - ceil(len(string) / 2.0))
    window.addstr(line, center, string)
    return center

def addstr_row(window, width, line, col0, col1, col2, col3, col4):
    window.addstr(line, 0,
                  ("{:<{x}} {:{x}} {:{x}}{:{x}} {:>{y}}").format\
                  (col0, col1, col2, col3, col4, x = width // 5,
                   y = width // 6))

def start_curses(stdscr, device, disk, partitions, free_space):
    max_yx = stdscr.getmaxyx()
    stdscr_cntr = partial(addstr_centered, stdscr, max_yx[1])
    stdscr_row  = partial(addstr_row, stdscr, max_yx[1])

    # Draw the device information.
    stdscr_cntr(0, "cparted 0.1")
    stdscr_cntr(2, "Disk Drive: %s (%s)" % (device.path, device.model))
    bytes_ = device.getSize('b')
    stdscr_cntr(3, "Size: %i bytes, %.1f GB" % (bytes_, (bytes_ / (10 ** 9))))
    stdscr_cntr(4, "Cylinders: %i Heads: %i  Sectors per Track: %i" %
                    device.biosGeometry)
    stdscr_cntr(5, "Partition Table: {:}".format(disk.type))
    stdscr_row(7,"Name", "Flags", "Part Type", "FS Type", "Size(MB)")
    stdscr.hline(8, 0, "-", max_yx[1])

    # Create the partitions menu.
    row = PART_TABLE
    partitions = sorted(list(partitions) + free_space,
                        key=lambda ps: ps.geometry.start)
    for part in partitions:
        stdscr_row(row, nodeName(part), flags(part), part_type(part),
                   fs_type(part), int(part.getSize('b') // 10**6))
        row += 1
    high_part = 0
    stdscr.chgat(PART_TABLE, 0, curses.A_STANDOUT)

    # Create the options menu.
    options_menu = OptMenu(stdscr, partitions[0])
    options_menu.draw_menu()

    # The main loop that captures user input.
    while True:
        key = stdscr.getkey()
        if key == "KEY_DOWN" or key == "KEY_UP":
            high_part = up_down(stdscr, key, high_part, len(partitions))
            options_menu.selected_option = 1 # Delete/New
            options_menu.partition(partitions[high_part])
            options_menu.draw_menu()
        if key == "KEY_RIGHT" or key == "KEY_LEFT":
            options_menu.left_right(key)
        if key == "q":
            break

def main():
    try:
        device = parted.Device(sys.argv[1])
        disk = parted.Disk(device)
        partitions = disk.partitions
        free_space = disk.getFreeSpacePartitions()
    except IndexError:
        sys.stderr.write("ERROR: you must enter a device path\n")
    except Exception, e:
        sys.stderr.write("ERROR: %s\n" % e)
    else:
        curses.wrapper(start_curses, device, disk, partitions, free_space)
    return 1
main()
