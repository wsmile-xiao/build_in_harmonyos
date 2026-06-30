# libbytesize

A C library for working with sizes in bytes, supporting arithmetic operations and unit conversion.

## Overview

libbytesize provides a library (libbytesize) and a Python wrapper for computing with arbitrary sizes in bytes. It supports operations like addition, subtraction, multiplication, division, modulo, and comparison of sizes expressed in bytes or human-readable units (KB, MB, GB, etc.). The library uses GMP and MPFR for arbitrary precision arithmetic.

## Key Features

- Arbitrary precision size computation using GMP/MPFR
- Human-readable size parsing and formatting (GiB, MiB, MB, etc.)
- Python bindings available (limited on HarmonyOS)
- bscalc command-line tool for quick size calculations (limited on HarmonyOS)

## OpenHarmony Compilation Status

| Version | Status | Date | Test Result |
|---------|--------|------|-------------|
| 2.11 | built | 2026-06-01 | C API ✅ (10/10 PASS), bscalc ⚠️ |

## Dependencies

- gmp >= 6.3.0 (shared library required, compile from source)
- mpfr >= 4.2.1
- gettext >= 0.22.5 (for NLS support; libintl.so.8 needs ELF signing)
- pcre2 >= 10.40
- **libintl_glib** (runtime: must link `-lintl_glib` for `g_libintl_dgettext` symbol)

## Platform Notes

### C API (✅ Fully Functional)

- Core operations (parse, add, sub, mul, div, cmp, convert) all pass on HarmonyOS
- **Critical**: Link with `-lintl_glib` when using libbytesize.so (provides `g_libintl_dgettext`)
- Compile example: `clang ... -lbytesize -lintl_glib -lintl -lgmp -lmpfr -lpcre2-8`

### bscalc Tool (⚠️ Limited)

- `#!/usr/bin/python3` shebang needs fix → `/data/service/hnp/python.org/python_3.12/bin/python3.12`
- ctypes dlopen restricted by HarmonyOS dynamic linker
- Use: `PYTHONPATH=$PREFIX/lib/python3.12/site-packages LD_PRELOAD=$PREFIX/lib/libintl_glib.so python bscalc`

### Autotools Adaptation

- Requires patched `config.guess` and `config.sub` for HarmonyOS detection (E007/E072)
- HMDFS `umask 077` must be patched to `022` in configure (E011)
- `install` command not available; use `ginstall` in Makefile.in (E080, R6)

## References

- Homepage: https://github.com/storaged-project/libbytesize
- License: LGPL-2.1-or-later