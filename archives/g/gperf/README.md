# gperf

GNU gperf is a perfect hash function generator. For a given list of strings, it produces a hash function and hash table, in form of C or C++ code, for looking up a string in a table.

## Description

Gperf generates a perfect hash function for a set of keywords. A perfect hash function is a hash function that maps keywords to hash values without any collisions. This allows for O(1) lookup time in the hash table.

## Features

- Generates perfect hash functions in C or C++
- Supports multiple input formats
- Configurable hash function parameters
- Generates efficient lookup code

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 3.1 | published | 2026-05-21 | Manual config generation due to HMDFS heredoc limitation |

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gperf 3.1
```

## Usage

```bash
gperf [OPTION]... [INPUT-FILE]

# Example: Generate hash function for C keywords
gperf -L C -N is_reserved_word keywords.gperf > hash.c
```

## License

GPL-3.0-or-later

## Links

- Homepage: https://www.gnu.org/software/gperf/
- Manual: https://www.gnu.org/software/gperf/manual/
- Repository: https://git.savannah.gnu.org/gitweb/?p=gperf.git

## Platform Notes

Due to HMDFS file system limitations, the standard autotools configure process cannot complete. Configuration files are generated manually using Python scripts. See version-specific notes.md for details.