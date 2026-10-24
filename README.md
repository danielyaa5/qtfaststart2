# qtfaststart2

[![Tests](https://github.com/danielyaa5/qtfaststart2/actions/workflows/test.yml/badge.svg)](https://github.com/danielyaa5/qtfaststart2/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/qtfaststart2)](https://pypi.org/project/qtfaststart2/)

Make QuickTime and MP4 files start playing before they finish downloading,
by moving the metadata (the `moov` atom) to the front of the file.

qtfaststart2 is a maintained fork of
[qtfaststart](https://github.com/danielgtaylor/qtfaststart), which hasn't been
updated since 2016. It's based on `qt-faststart.c` from FFmpeg and on
ISO 14496-12 (the MP4 spec). It's pure Python, so there's nothing to compile.

## Features

* Pure Python, works anywhere Python 3.7+ runs
* Handles 32-bit (`stco`) and 64-bit (`co64`) chunk offsets
* Handles files with several `mdat` atoms, and an `mdat` that runs to the
  end of the file
* Keeps the order of all other atoms, and drops `free` (padding) atoms
* Can replace the original file safely when no output file is given
* Leaves files that are already set up for streaming alone

## Install

```sh
pip install qtfaststart2
```

## Usage

```sh
qtfaststart2 input.mp4 output.mp4
```

If you leave out the output file, the input is replaced. The new file is
written next to the original first and only moved into place when it's
complete, and a file that's already optimised isn't touched.

```sh
qtfaststart2 video.mp4
```

Options:

| Option | What it does |
| --- | --- |
| `-l`, `--list` | List the top-level atoms and their sizes, in file order |
| `-s`, `--sample` | Write a small sample (the headers plus 4 MiB of each atom), handy for bug reports. Needs an output file |
| `-e`, `--to_end` | Move the `moov` atom to the end instead (for testing) |
| `-d`, `--debug` | Show debug output |

The exit code is 0 when the file was converted or was already optimised, and
1 when it couldn't be processed.

`python -m qtfaststart2 ...` works too.

## Python API

```python
from qtfaststart2 import processor
from qtfaststart2.exceptions import FastStartException

try:
    written = processor.process("input.mp4", "output.mp4")
except FastStartException as e:
    print("Couldn't process the file:", e)
else:
    if not written:
        print("Already optimised, nothing written")
```

`process()` returns `True` when it wrote the output file and `False` when the
input was already optimised (nothing is written then). Errors are subclasses of
`FastStartException`: `FastStartSetupError` (for example when input and output
are the same file), `MalformedFileError` and `UnsupportedFormatError`
(compressed `moov` atoms, or offsets that would pass 4 GiB in an `stco` atom).

`processor.get_index(open("input.mp4", "rb"))` returns the list of top-level
atoms as `(name, position, size)` tuples.

## Development

```sh
git clone https://github.com/danielyaa5/qtfaststart2
cd qtfaststart2
python -m unittest discover tests   # the ffmpeg test is skipped without ffmpeg
bin/qtfaststart2 --list some.mp4    # run without installing
```

To release, bump `VERSION` in `qtfaststart2/__init__.py`, add the version to
`CHANGES.md`, and publish a GitHub release tagged with the version number. The
publish workflow uploads it to PyPI.

## License

MIT, see [LICENSE.md](LICENSE.md).
