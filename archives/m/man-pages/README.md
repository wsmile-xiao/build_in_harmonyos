# man-pages

**Linux manual pages**

## Description

The man-pages project provides a collection of manual pages for the Linux operating system.
These pages document the system calls, library functions, and important file formats
available in Linux.

## Homepage

- https://www.kernel.org/doc/man-pages/

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 6.18 | built | 2026-05-28 | Documentation package only |

## Dependencies

- None (documentation only)

## Build System

- Makefile (simple install)

## Key Components

- System call documentation (section 2)
- Library function documentation (section 3)
- File format documentation (section 5)
- Administrative documentation (section 8)

## Installation

```bash
make install DESTDIR=/path/to/staging
```

## OpenHarmony Specific Notes

- No binary files (documentation only)
- Use GNU make (not toybox make)
- Requires GNU sed and coreutils for build
- G0 clean verify has platform limitations (Python subprocess)