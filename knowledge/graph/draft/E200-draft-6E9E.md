# E200: Python distutils build system (setup.py)

## Problem

PyCXX and similar Python extension frameworks use Python distutils (`setup.py`) as their build system, not autotools or cmake. When the ohc-run.py framework attempts to run `./configure` during G0 clean-verify, it fails because no configure script exists.

## Root Cause

- The software is a Python distutils project
- `setup.py` is the build entry point, not `./configure`
- DESTDIR mode uses `--root` parameter instead of `DESTDIR=` environment variable
- These are header-only + source libraries with no compiled binary outputs

## Solution

### Installation (DESTDIR mode)
```bash
python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX
```

`--root` is the Python distutils equivalent of DESTDIR.

### Verification
```bash
PYTHONPATH="$DEFAULT_PREFIX/lib/python3.12/site-packages" python3 -c "import CXX; print('CXX import OK')"
```

### Package
- Works with standard `ohc-run.py package` after verify-build passes
- No ELF binaries to sign (header-only library)

## Affected Software
- pycxx 6.2.8 (PyCXX C++ Python extension framework)
- Any Python distutils header-only library

## Key Points
1. No configure/make steps needed
2. `--root` = DESTDIR for Python distutils
3. `--prefix` sets the runtime installation path (R1: parameter minimization)
4. Manifest `build_system` field should be set to `script` (not `autotools`)
5. G0 clean-verify will fail (no configure script) — this is expected, not a real failure
