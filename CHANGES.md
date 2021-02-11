# Release notes
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

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
