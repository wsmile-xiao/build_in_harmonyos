# apg - Automated Password Generator

**Description**: APG (Automated Password Generator) is a tool for generating random passwords according to various rules and algorithms.

**Homepage**: https://github.com/wilx/apg

**License**: BSD-style (see COPYING file)

## Features

- Pronounceable password generation
- Random password generation with configurable modes
- Bloom filter dictionary check
- Password length control
- Character exclusion support
- Crypt password output (optional)

## Binaries

- **apg**: Main password generator
- **apgbfm**: Bloom filter management utility

## Usage Examples

```bash
# Generate 5 passwords (8-10 characters)
apg -n 5 -m 8 -x 10

# Generate pronounceable passwords
apg -a 0 -n 10

# Generate random passwords
apg -a 1 -n 10

# Exclude specific characters
apg -E "0123456789" -n 5

# Create bloom filter from dictionary
apgbfm -f myfilter -d dictionary.txt
```

## Compiled Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 2.2.3 | built | 2026-06-18 | Added getpass_compat for HarmonyOS |

## Dependencies

- No external library dependencies
- Uses musl libc (system library)

## Known Issues

- HarmonyOS requires getpass() compatibility implementation
- No automated test suite
- Makefile-based build (no configure script)