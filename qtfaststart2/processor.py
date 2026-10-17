"""
    The guts that actually do the work. This is available here for the
    'qtfaststart2' script and for your application's direct use.
"""

import bisect
import shutil
import logging
import os
import struct
import collections

import io

from qtfaststart2.exceptions import FastStartSetupError
from qtfaststart2.exceptions import MalformedFileError
from qtfaststart2.exceptions import UnsupportedFormatError

# This exception isn't directly used, included it for backward compatability
# in the event someone had used it from our namespace previously
from qtfaststart2.exceptions import FastStartException

CHUNK_SIZE = 8192

log = logging.getLogger("qtfaststart2")

# Older versions of Python require this to be defined
if not hasattr(os, 'SEEK_CUR'):
    os.SEEK_CUR = 1

Atom = collections.namedtuple('Atom', 'name position size')

def read_atom(datastream):
    """
        Read an atom and return a tuple of (size, type) where size is the size
        in bytes (including the 8 bytes already read) and type is a "fourcc"
        like "ftyp" or "moov".
    """
    size, type = struct.unpack(">L4s", datastream.read(8))
    # latin-1 maps every byte, so odd names like "\xa9nam" can't raise
    type = type.decode('latin-1')
    return size, type


def _read_atom_ex(datastream):
    """
    Read an Atom from datastream
    """
    pos = datastream.tell()
    atom_size, atom_type = read_atom(datastream)
    if atom_size == 1:
        atom_size, = struct.unpack(">Q", datastream.read(8))
    return Atom(atom_type, pos, atom_size)


def get_index(datastream):
    """
        Return an index of top level atoms, their absolute byte-position in the
        file and their size in a list:

        index = [
            ("ftyp", 0, 24),
            ("moov", 25, 2658),
            ("free", 2683, 8),
            ...
        ]

        The tuple elements will be in the order that they appear in the file.
    """
    log.debug("Getting index of top level atoms...")

    index = list(_read_atoms(datastream))
    _ensure_valid_index(index)

    return index


def _read_atoms(datastream):
    """
    Read atoms until an error occurs
    """
    datastream.seek(0, os.SEEK_END)
    eof = datastream.tell()
    datastream.seek(0)

    while True:
        try:
            atom = _read_atom_ex(datastream)
            log.debug("%s: %s" % (atom.name, atom.size))
        except Exception:
            break

        if atom.size == 0:
            if atom.name == "\x00\x00\x00\x00":
                # Strange zero atom with no size. Treat it as 8 bytes of junk
                # and keep looking for more atoms after it.
                yield atom._replace(size=8)
                continue

            # A size of zero means the atom runs to the end of the file (this
            # is common for a final mdat). Record its real size so it gets
            # copied, then stop as no more entries will be found!
            yield atom._replace(size=eof - atom.position)
            break

        if atom.size < 8:
            # Can't be a real atom, we're reading garbage
            log.warning("Invalid %r atom size %d at %d, ignoring the rest "
                        "of the file" % (atom.name, atom.size, atom.position))
            break

        yield atom

        datastream.seek(atom.position + atom.size)


def _ensure_valid_index(index):
    """
    Ensure the minimum viable atoms are present in the index.

    Raise MalformedFileError if not.
    """
    top_level_atoms = set([item.name for item in index])
    for key in ["moov", "mdat"]:
        if key not in top_level_atoms:
            msg = "%s atom not found, is this a valid MOV/MP4 file?" % key
            log.warning(msg)
            raise MalformedFileError(msg)


def find_atoms(size, datastream):
    """
    Compatibilty interface for _find_atoms_ex
    """
    fake_parent = Atom('fake', datastream.tell()-8, size+8)
    for atom in _find_atoms_ex(fake_parent, datastream):
        yield atom.name


def _find_atoms_ex(parent_atom, datastream):
    """
        Yield either "stco" or "co64" Atoms from datastream.
        datastream will be 8 bytes into the stco or co64 atom when the value
        is yielded.

        It is assumed that datastream will be at the end of the atom after
        the value has been yielded and processed.

        parent_atom is the parent atom, a 'moov' or other ancestor of CO
        atoms in the datastream.
    """
    stop = parent_atom.position + parent_atom.size

    while datastream.tell() < stop:
        try:
            atom = _read_atom_ex(datastream)
        except Exception:
            msg = "Error reading next atom!"
            log.exception(msg)
            raise MalformedFileError(msg)

        if atom.size < 8:
            msg = "Invalid %r atom size %d at %d" % (
                atom.name, atom.size, atom.position)
            log.error(msg)
            raise MalformedFileError(msg)

        if atom.name in ["trak", "mdia", "minf", "stbl"]:
            # Known ancestor atom of stco or co64, search within it!
            for res in _find_atoms_ex(atom, datastream):
                yield res
        elif atom.name in ["stco", "co64"]:
            yield atom
        else:
            # Ignore this atom, seek to the end of it.
            datastream.seek(atom.position + atom.size)

def _moov_is_compressed(datastream, moov_atom):
    """
        scan the atoms under the moov atom and detect whether or not the
        atom data is compressed
    """
    # seek to the beginning of the moov atom contents
    datastream.seek(moov_atom.position+8)

    # step through the moov atom childeren to see if a cmov atom is among them
    stop = moov_atom.position + moov_atom.size
    while datastream.tell() < stop:
        try:
            child_atom = _read_atom_ex(datastream)
        except Exception:
            msg = "Error reading moov atom children!"
            log.exception(msg)
            raise MalformedFileError(msg)

        if child_atom.size < 8:
            msg = "Invalid %r atom size %d at %d" % (
                child_atom.name, child_atom.size, child_atom.position)
            log.error(msg)
            raise MalformedFileError(msg)

        datastream.seek(child_atom.position + child_atom.size)

        # cmov means compressed moov header!
        if child_atom.name == 'cmov':
            return True

    return False

def process(infilename, outfilename, limit=float('inf'), to_end=False,
        cleanup=True):
    """
        Convert a Quicktime/MP4 file for streaming by moving the metadata to
        the front of the file. This method writes a new file.

        Returns True if outfilename was written, or False if the file was
        already optimised for streaming, in which case nothing is written.

        If limit is set to something other than zero it will be used as the
        number of bytes to write of the atoms following the moov atom. This
        is very useful to create a small sample of a file with full headers,
        which can then be used in bug reports and such.

        If cleanup is set to False, free atoms and zero atoms will not be
        scrubbed from from the mov
    """
    if os.path.exists(outfilename) and os.path.samefile(infilename,
                                                        outfilename):
        # Opening the output would truncate the input before it is read
        msg = "Input and output are the same file. Leave out the output " \
              "filename to replace the input file."
        log.error(msg)
        raise FastStartSetupError(msg)

    with open(infilename, "rb") as datastream:
        return _process(datastream, infilename, outfilename, limit, to_end,
                        cleanup)


def _process(datastream, infilename, outfilename, limit, to_end, cleanup):
    # Get the top level atom index
    index = get_index(datastream)

    mdat_atoms = [atom for atom in index if atom.name == "mdat"]
    mdat_pos_first = mdat_atoms[0].position
    mdat_pos_last = mdat_atoms[-1].position

    # The atoms are guaranteed to exist from get_index above!
    moov_atom = [atom for atom in index if atom.name == "moov"][-1]

    # Atoms left out of the output
    dropped = []
    for atom in index:
        if atom.name == "free" and cleanup:
            dropped.append(atom)
        elif atom.name == "\x00\x00\x00\x00":
            # This is some strange zero atom with incorrect size
            dropped.append(atom)

    for atom in dropped:
        if atom.position < mdat_pos_first:
            log.info("Removing %s atom at %d (%d bytes)" % (
                "free" if atom.name == "free" else "strange zero",
                atom.position, atom.size))

    if to_end:
        moov_misplaced = moov_atom.position < mdat_pos_last
    else:
        moov_misplaced = moov_atom.position > mdat_pos_first

    if not moov_misplaced and not any(atom.position < mdat_pos_first
                                      for atom in dropped):
        # No free atoms to process and moov is correct, we are done!
        msg = "This file appears to be already optimised for streaming. Nothing to do."
        log.info(msg)
        return False

    # Check for compressed moov atom
    is_compressed = _moov_is_compressed(datastream, moov_atom)
    if is_compressed:
        msg = "Movies with compressed headers are not supported"
        log.error(msg)
        raise UnsupportedFormatError(msg)

    # Work out the output layout: ftyp, moov, then everything else in order
    # (or moov last when moving it to the end)
    ftyp_atoms = [atom for atom in index if atom.name == "ftyp"]
    rest = [atom for atom in index
            if atom.name not in ("ftyp", "moov") and atom not in dropped]
    if to_end:
        layout = ftyp_atoms + rest + [moov_atom]
    else:
        layout = ftyp_atoms + [moov_atom] + rest

    # Each chunk offset moves by however far its enclosing atom moved
    moved = []
    new_pos = 0
    for atom in layout:
        moved.append((atom.position, new_pos - atom.position))
        new_pos += atom.size
    moved.sort()

    # read and fix moov
    moov = _patch_moov(datastream, moov_atom, moved)

    log.info("Writing output...")
    try:
        with open(outfilename, "wb") as outfile:
            for i, atom in enumerate(layout):
                if atom is moov_atom:
                    _write_moov(moov, outfile)
                    continue

                log.debug("Writing %s... (%d bytes)" % (atom.name, atom.size))
                datastream.seek(atom.position)

                if i < len(layout) - 1 and _has_zero_size(datastream, atom):
                    # This atom ran to the end of the file, but no longer
                    # does, so give it a real size
                    _write_real_size(datastream, atom, outfile)

                # for compatability, allow '0' to mean no limit
                cur_limit = limit or float('inf')
                if atom.name == "ftyp":
                    cur_limit = float('inf')
                cur_limit = min(cur_limit, atom.size - (
                    datastream.tell() - atom.position))

                for chunk in get_chunks(datastream, CHUNK_SIZE, cur_limit):
                    outfile.write(chunk)
    except BaseException:
        # Don't leave a half written file behind
        try:
            os.remove(outfilename)
        except OSError:
            pass
        raise

    # Set permissions
    try:
        shutil.copymode(infilename, outfilename)
    except Exception:
        log.warning("Could not copy file permissions!")

    return True

def _has_zero_size(datastream, atom):
    datastream.seek(atom.position)
    size, = struct.unpack(">L", datastream.read(4))
    datastream.seek(atom.position)
    return size == 0

def _write_real_size(datastream, atom, outfile):
    if atom.size > 0xFFFFFFFF:
        msg = "Can't move the moov atom after a %s atom over 4 GiB " \
              "with no size set" % atom.name
        log.error(msg)
        raise UnsupportedFormatError(msg)

    outfile.write(struct.pack(">L", atom.size))
    datastream.seek(atom.position + 4)

def _write_moov(moov, outfile):
    # Write moov
    bytes = moov.getvalue()
    log.debug("Writing moov... (%d bytes)" % len(bytes))
    outfile.write(bytes)

def _patch_moov(datastream, atom, moved):
    """
        Read the moov atom and fix every chunk offset in it. moved is a
        sorted list of (old atom position, distance moved) for every atom
        in the output.
    """
    datastream.seek(atom.position)
    moov = io.BytesIO(datastream.read(atom.size))

    # reload the atom from the fixed stream
    atom = _read_atom_ex(moov)

    starts = [position for position, _ in moved]

    def new_offset(entry):
        # Find the atom the chunk lives in
        i = max(bisect.bisect_right(starts, entry) - 1, 0)
        return entry + moved[i][1]

    for atom in _find_atoms_ex(atom, moov):
        # Read either 32-bit or 64-bit offsets
        ctype, csize = dict(
            stco=('L', 4),
            co64=('Q', 8),
        )[atom.name]

        # Get number of entries
        version, entry_count = struct.unpack(">2L", moov.read(8))

        log.info("Patching %s with %d entries" % (atom.name, entry_count))

        entries_pos = moov.tell()

        struct_fmt = ">%(entry_count)s%(ctype)s" % vars()

        # Read entries
        entries = struct.unpack(struct_fmt, moov.read(csize * entry_count))

        # Patch and write entries
        offset_entries = [new_offset(entry) for entry in entries]
        if atom.name == "stco" and offset_entries and \
                max(offset_entries) > 0xFFFFFFFF:
            msg = "Chunk offsets would go past 4 GiB, which needs a co64 " \
                  "atom instead of stco. This is not supported yet."
            log.error(msg)
            raise UnsupportedFormatError(msg)
        moov.seek(entries_pos)
        moov.write(struct.pack(struct_fmt, *offset_entries))
    return moov

def get_chunks(stream, chunk_size, limit):
    remaining = limit
    while remaining:
        chunk = stream.read(min(remaining, chunk_size))
        if not chunk:
            return
        remaining -= len(chunk)
        yield chunk
