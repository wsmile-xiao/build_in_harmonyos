# 4ti2

A software package for algebraic, geometric and combinatorial problems on linear spaces.

## Homepage
https://4ti2.de/

## License
GPL-2.0-or-later

## Build System
Autotools (configure + make)

## Dependencies
- GMP (GNU Multiple Precision Arithmetic Library) — with C++ interface
- GLPK (GNU Linear Programming Kit)

## OHOS Adaptation
- config.guess cannot recognize OHOS — pass `--build/--host=aarch64-unknown-linux-musl`
- config.status `mktemp -d` with `umask 077` creates directories with setgid but no group-execute — patched to use `mkdir`
- Test scripts use `#!/bin/bash` but bash at `/data/service/hnp/bin/bash` — test/*.in templates patched BEFORE configure so generated scripts work
- `CONFIG_SHELL` must be set to `/data/service/hnp/bin/bash`

## Versions
- 1.6.10 — built 2026-09-17 (R34 real API test + upstream make check 231/235 + API 4/4 on device)
