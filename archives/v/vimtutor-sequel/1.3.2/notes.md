# Notes — vimtutor-sequel 1.3.2

## Build Summary

`vimtutor-sequel` is a pure shell-script command-line tool. Upstream ships:

- `vimtutor-sequel.sh`
- `vimtutor-sequel.txt`
- `vimtutor-sequel.vimrc`

There is no configure script, compiler, or native build system.

## HarmonyOS PC Adaptation

### 1. Homebrew-only path logic

Upstream assumes:

- `brew --prefix`
- `share/vimtutor-sequel/...`

That fails inside a Conan package on HarmonyOS PC. The package patch rewrites
the script to derive `share/vimtutor-sequel` from the installed script location
(`bin/../share/vimtutor-sequel`).

### 2. Hardcoded shell and temporary file path

Upstream uses:

- `#!/bin/bash`
- `/tmp/vimtutor-sequel.txt`

HarmonyOS PC packaging is more reliable with:

- `#!/usr/bin/env bash`
- `mktemp` under `${TMPDIR:-/tmp}`

This avoids shell-path assumptions and fixed-name temp-file conflicts.

### 3. Avoiding conan-build-test timeouts

Running the real tutorial launches interactive Vim, which would block CI.
Therefore `test_package` only performs:

1. package layout verification (`bin/` + `share/`)
2. `vimtutor-sequel --version`
3. script-content assertions proving the Homebrew-specific path logic is gone

This keeps the test real while remaining non-interactive.

## Upstream Tests

No upstream automated `make check` / `ctest` / `pytest` suite is shipped in the
v1.3.2 source archive. Consumer-facing validation is implemented in
`test_package/`.
