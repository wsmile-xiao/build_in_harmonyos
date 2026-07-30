# Test Report — when 1.1.45

## Build Environment
- OS: OpenHarmony 6.0 (aarch64)
- Build system: Makefile (Perl application)
- Perl: 5.42.0
- Compiler: clang 15.0.4

## Build Steps
1. `make when.1` — Generate manpage from POD via pod2man
2. `make install` — Install Perl script and manpage

## Test Results

### make test
- **Status**: PASSED
- **Tests**: 44 expression tests + 1 accent filtering test
- All tests passed after creating ~/.when/preferences and ~/calendar files

### Version Check
```
$ when --version
When version 1.1.45, (c) 2003-2011 Benjamin Crowell.
```

## Notes
- "when" is a Perl-based personal calendar application, not a C/C++ project
- Tests require a preferences file (~/.when/preferences) and a calendar file (~/calendar) to be present
- No patches needed — the build is straightforward (pod2man generates manpage)
