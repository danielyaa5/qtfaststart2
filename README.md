# Quicktime/MP4 Fast Start
Forked from [qtfaststart](https://github.com/danielgtaylor/qtfaststart) which 
has had no maintainer for many years.


Enable streaming and pseudo-streaming of Quicktime and MP4 files by
moving metadata and offset information to the front of the file.

This program is based on qt-faststart.c from the ffmpeg project, which is
released into the public domain, as well as ISO 14496-12:2005 (the official
spec for MP4), which can be obtained from the ISO or found online.

The goals of this project are to run anywhere without compilation (in
particular, many Windows and Mac OS X users have trouble getting
qt-faststart.c compiled), to run about as fast as the C version, to be more
user-friendly, and to use less actual lines of code doing so.

## Features
* Works everywhere Python (2.6+) can be installed
* Handles both 32-bit (stco) and 64-bit (co64) atoms
* Handles any file where the mdat atom is before the moov atom
* Preserves the order of other atoms
* Can replace the original file (if given no output file)
  Installing from source
----------------------

Download a copy of the source, ``cd`` into the top-level
``qtfaststart2`` directory, and run::

    python setup.py install

If you are installing to your system Python (instead of a virtualenv), you
may need root access (via ``sudo`` or ``su``).

## Usage
See ``qtfaststart2 --help`` for more info! If outfile is not present then
the infile is overwritten::

    $ qtfaststart2 infile [outfile]

To run without installing you can use::

    $ bin/qtfaststart2 infile [outfile]

To see a list of top-level atoms and their order in the file::

    $ bin/qtfaststart2 --list infile

If on Windows, the qtfaststart2 script will not execute, so use::

    > python -m qtfaststart2 ...

