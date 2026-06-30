# pycxx

PyCXX — C++ facilities for extending Python with C++.

PyCXX provides a set of C++ classes to make it easier to write Python extensions.
It wraps the Python C API to provide a more C++-like interface.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 6.2.8 | built | 2026-06-23 |

## Description

PyCXX is a header-only + source library. The main products are:
- C++ header files (.hxx, .h) installed to `include/python3.12/CXX/`
- C++ support source files (.cxx, .c) installed to `share/python3.12/CXX/`
- Python package wrapper installed to `lib/python3.12/site-packages/CXX/`

## Build System

Python distutils (setup.py). No configure/make required.
