# pgsanity

pgsanity is a command-line tool that checks the syntax of PostgreSQL SQL files. It validates SQL statements by using PostgreSQL's parser to identify syntax errors before execution.

## Key Information

- **Homepage**: https://github.com/markdrago/pgsanity
- **License**: MIT
- **Language**: Python (pure Python, no C/C++ code)
- **Dependencies**: Python 3.9+ (no other dependencies)

## HarmonyOS Adaptation

- pgsanity is a pure Python package installed via pip wheel
- No C/C++ compilation needed; installed directly using the pre-built wheel
- The pip-generated entry point script shebang must be changed from the direct Python binary path to `/usr/bin/env python3` (HarmonyOS uses a bash wrapper script for python3 that properly sets LD_LIBRARY_PATH)
- Requires Python 3.9+ on the target HarmonyOS system

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 0.3.0 | published | 2026-06-12 |