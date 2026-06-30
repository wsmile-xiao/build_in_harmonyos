# mon

## Description
mon is a simple monitoring tool that monitors hosts/services/whatever and alerts about problems.
It is written in C and uses a simple Makefile build system.

## Versions
- 1.2.3 (published, 2026-06-25)

## Build System
- Type: makefile (simple Makefile, no configure script)
- Compiler: clang
- Dependencies: none

## Notes
- mon uses a simple Makefile with no autotools configure script
- A configure wrapper script was added to support clean-verify G0
- DESTDIR support was added to the Makefile install target
- No test suite available
