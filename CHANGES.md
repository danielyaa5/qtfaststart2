# Release notes
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## Unreleased
- Fix: running on an already optimised file with no output filename replaced the file with an empty one.
  See https://github.com/danielyaa5/qtfaststart2/pull/1
- Fix: passing the same file as input and output destroyed it. This is now an error.
- Fix: an mdat atom with size 0 (running to the end of the file) was written out as nothing.
- Fix: chunk offsets were wrong when the moov or a free atom sat between two mdat atoms.
- Fail with a clear error instead of crashing when moving moov would push stco offsets past 4 GiB.
- Invalid atom sizes now raise MalformedFileError instead of looping forever.
- `process()` now returns True when it wrote a file and False when the file was already optimised.
- Replacing a file in place now writes the temporary file next to it, and never leaves it behind.
- Files are closed properly, and `log.warn` is replaced by `log.warning`.
- Add tests: `python -m unittest discover tests`

## 2.1.1
- Readme updates, skipped a few versions here because of an accidental mess-up with PyPi publishing

## 2.0.3
- Fix import errors by renaming everything from qtfaststart to qtfaststart2

## 2.0.2
- Fix: Exit gracefully on already optimised files. See https://github.com/danielgtaylor/qtfaststart/pull/17

## 2.0.1
- Support files with multiple mdat atoms. qtfaststart2 can mistakenly handle files with multiple mdat atoms as already
  set up when the moov atom is actually at the end of the file. This patch makes certain the moov atom is placed before
  all mdat atoms. See https://github.com/danielgtaylor/qtfaststart/pull/19

## 2.0.0
- Create qtfaststart2 which is branched off from [danielgtaylor/qtfaststart](https://github.com/danielgtaylor/qtfaststart)
