# Miller

Miller is a command-line tool for querying, shaping, and reformatting CSV, TSV, JSON, and other tabular data formats. It provides powerful data processing capabilities similar to awk, sed, cut, join, and sort, but for structured data.

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 6.15.0-r7 | published | 2026-06-04 |

## Key Features
- CSV, TSV, JSON, and other format support
- Filtering, sorting, aggregating, reshaping data
- Format conversion (CSV to JSON, etc.)
- Streaming processing for large files

## Build Notes
- Go project with custom Makefile-based build system
- Requires Go 1.24.2+
- Configure script is non-standard (modifies PREFIX in Makefile)
- ELF signing required for HarmonyOS execution