# Breakpad

Google Breakpad — a set of client and server components for crash reporting.

## Overview

Breakpad is a library and suite of tools for generating and processing
crash dumps. It consists of:

- **libbreakpad.a** — core minidump generation library
- **libbreakpad_client.a** — client-side exception handler library
- **dump_syms** — symbol file generator (converts debug info to Breakpad format)
- **minidump_stackwalk** — stack walker for minidump files
- **minidump_dump** — minidump file inspector

## Versions

| Version | Status | Build System | Date |
|---------|--------|-------------|------|
| v2023.06.01 | built | autotools | 2026-06-25 |

## License

BSD-3-Clause

## Homepage

https://github.com/google/breakpad
