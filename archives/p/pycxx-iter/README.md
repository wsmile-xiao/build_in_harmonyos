# pycxx-iter

PyCXX 6.2.8 demo extension module - part of the PyCXX C++ Python extension framework.

## Description
pycxx-iter is a demonstration Python C extension built using the PyCXX library, compiled for OpenHarmony (aarch64) with Python 3.12.

## Version
- 6.2.8 (matches PyCXX core version)

## Dependencies
- Python 3.12
- PyCXX core library (pycxx 6.2.8)

## Build
Uses setup_makefile.py to generate a Makefile, then make to compile the .so extension.

## Known Platform Limitations
- .so import blocked by HMDFS SELinux policy (use embedding mode or deploy via cmd-pkgs)
