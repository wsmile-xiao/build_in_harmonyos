# perl-posix-strftime-compiler

POSIX::strftime::Compiler — GNU C library compatible strftime for loggers and servers.

## Description

Provides a GNU C library compatible strftime implementation that compiles
format strings for better performance. Useful for loggers and servers that
need consistent strftime behavior.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.46 | published | 2026-06-25 |

## Patches

| Patch | Type | Description |
|-------|------|-------------|
| 0001-Makefile.PL.patch | build-system | Create Makefile.PL (original uses Module::Build::Tiny, not available) |
| 0001-lib-POSIX-strftime-Compiler.pm.patch | bugfix | Fix 12-hour clock: %I/%l give 01 instead of 12 for hours 0/12; %p/%P inverted AM/PM for noon/midnight |

## Test Results

- Original test suite: 371/371 PASS
- Comprehensive functional tests: 91/91 PASS
- Bug fix verified: 12-hour clock output now matches POSIX::strftime

## Links

- CPAN: https://metacpan.org/release/POSIX-strftime-Compiler
- Repository: https://github.com/kazeburo/POSIX-strftime-Compiler
