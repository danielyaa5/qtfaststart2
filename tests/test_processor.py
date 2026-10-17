"""
    Tests for qtfaststart2. Run with:

        python -m unittest discover tests
"""

import hashlib
import io
import logging
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qtfaststart2 import processor
from qtfaststart2.exceptions import FastStartSetupError
from qtfaststart2.exceptions import UnsupportedFormatError

logging.getLogger("qtfaststart2").setLevel(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = shutil.which("ffmpeg") if hasattr(shutil, "which") else None


def box(name, payload=b"", size=None):
    if size is None:
        size = len(payload) + 8
    return struct.pack(">L4s", size, name.encode("latin-1")) + payload


def chunk(n):
    # Every chunk starts with a unique marker so tests can check that the
    # patched offsets still point at the right bytes
    return ("CHUNK%03d" % n).encode("ascii") * 4


class Layout(object):
    """
        Build a small MP4-like file. parts is a list of:

            ("ftyp",) ("free",) ("moov",) ("mdat", [chunk numbers])
            ("mdat0", [chunk numbers])  - mdat with size 0, running to EOF
    """

    def __init__(self, parts, co64=False):
        self.parts = parts
        self.co64 = co64
        self.chunks = {}

        # moov size doesn't depend on the offsets, so build it twice
        self.data = self._build(self._moov({}))
        self.data = self._build(self._moov(self.offsets))

    def _moov(self, offsets):
        numbers = sorted(self.chunks) or [n for p in self.parts if len(p) > 1
                                          for n in p[1]]
        entries = [offsets.get(n, 0) for n in numbers]
        if self.co64:
            co = box("co64", struct.pack(">2L", 0, len(entries)) +
                     struct.pack(">%dQ" % len(entries), *entries))
        else:
            co = box("stco", struct.pack(">2L", 0, len(entries)) +
                     struct.pack(">%dL" % len(entries), *entries))
        stbl = box("stbl", box("stsd", b"\0" * 8) + co)
        trak = box("trak", box("tkhd", b"\0" * 12) +
                   box("mdia", box("minf", stbl)))
        return box("moov", box("mvhd", b"\0" * 20) + trak)

    def _build(self, moov):
        out = io.BytesIO()
        self.offsets = {}
        for part in self.parts:
            name = part[0]
            if name == "ftyp":
                out.write(box("ftyp", b"isom\0\0\x02\0isomiso2"))
            elif name == "free":
                out.write(box("free", b"\0" * 16))
            elif name == "moov":
                out.write(moov)
            elif name in ("mdat", "mdat0"):
                start = out.tell()
                payload = b""
                for n in part[1]:
                    self.offsets[n] = start + 8 + len(payload)
                    self.chunks[n] = chunk(n)
                    payload += chunk(n)
                out.write(box("mdat", payload,
                              size=0 if name == "mdat0" else None))
        return out.getvalue()


def top_level(data):
    atoms = []
    pos = 0
    while pos + 8 <= len(data):
        size, name = struct.unpack(">L4s", data[pos:pos + 8])
        if size == 0:
            size = len(data) - pos
        atoms.append((name.decode("latin-1"), pos, size))
        pos += size
    return atoms


def chunk_offsets(data):
    moov = [a for a in top_level(data) if a[0] == "moov"][0]
    offsets = []

    def walk(start, stop):
        pos = start
        while pos < stop:
            size, name = struct.unpack(">L4s", data[pos:pos + 8])
            name = name.decode("latin-1")
            if name in ("trak", "mdia", "minf", "stbl"):
                walk(pos + 8, pos + size)
            elif name in ("stco", "co64"):
                count, = struct.unpack(">L", data[pos + 12:pos + 16])
                fmt = ">%d%s" % (count, "L" if name == "stco" else "Q")
                offsets.extend(struct.unpack(
                    fmt, data[pos + 16:pos + 16 + struct.calcsize(fmt)]))
            pos += size

    walk(moov[1] + 8, moov[1] + moov[2])
    return offsets


class ProcessTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def path(self, name):
        return os.path.join(self.dir, name)

    def write(self, name, data):
        with open(self.path(name), "wb") as f:
            f.write(data)
        return self.path(name)

    def read(self, name):
        with open(self.path(name), "rb") as f:
            return f.read()

    def assert_chunks_intact(self, layout, data):
        offsets = chunk_offsets(data)
        numbers = sorted(layout.chunks)
        self.assertEqual(len(offsets), len(numbers))
        for n, offset in zip(numbers, offsets):
            expected = layout.chunks[n]
            self.assertEqual(data[offset:offset + len(expected)], expected,
                             "chunk %d points at the wrong bytes" % n)

    def run_layout(self, parts, **kwargs):
        layout = Layout(parts, co64=kwargs.pop("co64", False))
        # The input itself must be consistent
        self.assert_chunks_intact(layout, layout.data)
        infile = self.write("in.mp4", layout.data)
        self.assertTrue(processor.process(infile, self.path("out.mp4"),
                                          **kwargs))
        out = self.read("out.mp4")
        self.assert_chunks_intact(layout, out)
        return out

    def names(self, data):
        return [a[0] for a in top_level(data)]

    def test_moov_at_end(self):
        out = self.run_layout([("ftyp",), ("free",), ("mdat", [1, 2, 3]),
                               ("moov",)])
        self.assertEqual(self.names(out), ["ftyp", "moov", "mdat"])

    def test_co64(self):
        out = self.run_layout([("ftyp",), ("mdat", [1, 2]), ("moov",)],
                              co64=True)
        self.assertEqual(self.names(out), ["ftyp", "moov", "mdat"])

    def test_moov_between_mdats(self):
        out = self.run_layout([("ftyp",), ("mdat", [1, 2]), ("moov",),
                               ("mdat", [3, 4])])
        self.assertEqual(self.names(out), ["ftyp", "moov", "mdat", "mdat"])

    def test_free_between_mdats(self):
        out = self.run_layout([("ftyp",), ("mdat", [1, 2]), ("free",),
                               ("mdat", [3, 4]), ("moov",)])
        self.assertEqual(self.names(out), ["ftyp", "moov", "mdat", "mdat"])

    def test_keep_free_atoms(self):
        out = self.run_layout([("ftyp",), ("free",), ("mdat", [1, 2]),
                               ("free",), ("mdat", [3]), ("moov",)],
                              cleanup=False)
        self.assertEqual(self.names(out),
                         ["ftyp", "moov", "free", "mdat", "free", "mdat"])

    def test_zero_size_mdat_is_copied(self):
        layout = Layout([("ftyp",), ("moov",), ("free",), ("mdat0", [1, 2])])
        out = self.run_layout(layout.parts)
        self.assertEqual(self.names(out), ["ftyp", "moov", "mdat"])
        # All of mdat was copied, not zero bytes of it
        self.assertEqual(len(out), len(layout.data) - 24)

    def test_zero_size_mdat_to_end(self):
        out = self.run_layout([("ftyp",), ("moov",), ("mdat0", [1, 2])],
                              to_end=True)
        self.assertEqual(self.names(out), ["ftyp", "mdat", "moov"])
        # mdat must now carry its real size or it would swallow moov
        mdat = top_level(out)[1]
        self.assertNotEqual(struct.unpack(">L", out[mdat[1]:mdat[1] + 4])[0],
                            0)

    def test_to_end(self):
        out = self.run_layout([("ftyp",), ("moov",), ("mdat", [1, 2])],
                              to_end=True)
        self.assertEqual(self.names(out), ["ftyp", "mdat", "moov"])

    def test_already_optimised(self):
        layout = Layout([("ftyp",), ("moov",), ("mdat", [1])])
        infile = self.write("in.mp4", layout.data)
        self.assertFalse(processor.process(infile, self.path("out.mp4")))
        self.assertFalse(os.path.exists(self.path("out.mp4")))

    def test_same_input_and_output(self):
        layout = Layout([("ftyp",), ("mdat", [1]), ("moov",)])
        infile = self.write("in.mp4", layout.data)
        self.assertRaises(FastStartSetupError, processor.process, infile,
                          infile)
        self.assertEqual(self.read("in.mp4"), layout.data)

    def test_stco_overflow(self):
        layout = Layout([("ftyp",), ("mdat", [1]), ("moov",)])
        moov = [a for a in top_level(layout.data) if a[0] == "moov"][0]
        stream = io.BytesIO(layout.data)
        atom = processor.Atom("moov", moov[1], moov[2])
        self.assertRaises(UnsupportedFormatError, processor._patch_moov,
                          stream, atom, [(0, 2 ** 32)])

    def test_odd_atom_names(self):
        layout = Layout([("ftyp",), ("mdat", [1]), ("moov",)])
        data = layout.data + box("\xa9xyz", b"abc")
        index = processor.get_index(io.BytesIO(data))
        self.assertEqual(index[-1].name, "\xa9xyz")


class CommandTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def run_cli(self, *args):
        return subprocess.call([sys.executable, "-m", "qtfaststart2"] +
                               list(args), cwd=ROOT,
                               stdout=subprocess.DEVNULL)

    def test_in_place_already_optimised_keeps_file(self):
        data = Layout([("ftyp",), ("moov",), ("mdat", [1, 2])]).data
        path = os.path.join(self.dir, "video.mp4")
        with open(path, "wb") as f:
            f.write(data)

        self.assertEqual(self.run_cli(path), 0)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), data)
        self.assertEqual(os.listdir(self.dir), ["video.mp4"])

    def test_in_place(self):
        layout = Layout([("ftyp",), ("mdat", [1, 2]), ("moov",)])
        path = os.path.join(self.dir, "video.mp4")
        with open(path, "wb") as f:
            f.write(layout.data)
        os.chmod(path, 0o644)

        self.assertEqual(self.run_cli(path), 0)
        with open(path, "rb") as f:
            out = f.read()
        self.assertEqual([a[0] for a in top_level(out)],
                         ["ftyp", "moov", "mdat"])
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o644)
        self.assertEqual(os.listdir(self.dir), ["video.mp4"])

    def test_in_place_error_leaves_no_temp_file(self):
        path = os.path.join(self.dir, "video.mp4")
        with open(path, "wb") as f:
            f.write(b"not a video at all")

        self.assertEqual(self.run_cli(path), 1)
        self.assertEqual(os.listdir(self.dir), ["video.mp4"])


@unittest.skipUnless(FFMPEG, "ffmpeg not installed")
class FfmpegTests(unittest.TestCase):
    """
        Check real files made by ffmpeg still decode to the same frames
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def framemd5(self, path):
        out = subprocess.check_output([FFMPEG, "-v", "error", "-i", path,
                                       "-f", "framemd5", "-"])
        lines = [l for l in out.splitlines() if not l.startswith(b"#")]
        return hashlib.md5(b"\n".join(lines)).hexdigest()

    def test_video_and_audio(self):
        src = os.path.join(self.dir, "src.mp4")
        subprocess.check_call([
            FFMPEG, "-v", "error", "-f", "lavfi", "-i",
            "testsrc=size=160x120:rate=25", "-f", "lavfi", "-i",
            "sine=frequency=440", "-t", "2", "-c:v", "mpeg4", "-c:a", "aac",
            src])
        out = os.path.join(self.dir, "out.mp4")
        self.assertTrue(processor.process(src, out))
        self.assertEqual([a.name for a in processor.get_index(
            open(out, "rb"))][:2], ["ftyp", "moov"])
        self.assertEqual(self.framemd5(src), self.framemd5(out))


if __name__ == "__main__":
    unittest.main()
