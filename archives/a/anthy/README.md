# Anthy - Japanese Input Method Engine

Anthy is a Japanese input method engine that converts Hiragana text to Kana Kanji mixed text.

## Overview

Anthy provides a library for Japanese text conversion and command-line tools for testing and dictionary management.

## Components

- **libanthy**: Main conversion library
- **libanthydic**: Dictionary library
- **libanthyinput**: Input method library
- **anthy-agent**: Command-line input agent
- **anthy-dic-tool**: Dictionary management tool

## OHOS Adaptation Notes

### Key Issues

1. **config.guess/config.sub modification (E007)**: GNU config scripts don't recognize HarmonyOS. Added HarmonyOS detection branches and ohos-linux support.

2. **umask permission issue (E011)**: HMDFS file system UID mapping causes permission errors when config.status creates temporary directories with umask 077. Fixed by changing umask to 022.

3. **Legacy config.guess (E007 FAQ)**: 2018-version config.guess uses `echo+exit` syntax instead of `GUESS=` variable. Modified to use echo+exit for HarmonyOS output.

### Patches Applied

- `0001-build-aux-config.guess.patch`: HarmonyOS system identification
- `0002-build-aux-config.sub.patch`: ohos-linux and linux-ohos* support
- `0003-configure.patch`: umask 077 → umask 022

## Build Information

| Version | Status | Date |
|---------|--------|------|
| 0.4 | built | 2026-06-18 |

## Usage

```bash
# Check version
anthy-agent --version

# Dictionary tool
anthy-dic-tool --version

# Dump dictionary
anthy-dic-tool --dump

# Help
anthy-dic-tool --help
```

## Test Report

See `0.4/reports/test-report.md` for detailed functionality test results.

**Test Summary**: 91.3% pass rate (21/23 items)
- ✅ Command-line tools executable
- ✅ Libraries correctly installed (12 files + symlinks)
- ✅ Dictionary files present (22.7MB)
- ✅ RPATH configured correctly
- ✅ ELF signatures verified

## License

- GPL-2.0-or-later (for main library)
- LGPL-2.1-or-later (for dictionary and input libraries)

## References

- Official Site: https://osdn.net/projects/anthy/
- Debian Package: anthy_0.4