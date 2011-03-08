TODO List
=========

1. Figure out what to do with the Type option.
    * Can parted correctly determine partition types?
    * Does changing the partition type matter or make sense?

2. Figure out what to do with the Maximize option.
    * What exactly does the cfdisk version of this do?
    * Does pyparted have something that is eqiuvalent?
    * If implemented, ought this to grow the fs as gparted can do?

3. Should btrfs be supported, if so, how?

4. Should we support grow, shrink, move, and create fs operations?

5. Create a man page.

6. Should we show labels as cfdisk does?

7. Does anyone really care about the Bootable option?

8. Fix the "gaps" issue.

9. Implement the Print option.

10. Provide a usage message when wrong input is given at startup.
