# yascreen

Yet another screen library — a small terminal screen control library by Boian
Bonev. It provides double-buffered screen updates, wide/unicode cell handling,
virtual/screen/telnet input modes and a tiny API suitable for fullscreen
console applications.

- Upstream: https://github.com/bbonev/yascreen
- License: LGPL-3.0-or-later
- Adapted versions: `2.13/`

## Adaptation summary (2.13)

- Raw `GNUmakefile` build driven directly (upstream `Makefile` wrapper demands
  `gmake`, absent on the target).
- `AR`/`RANLIB` overridden with `llvm-ar`/`llvm-ranlib` on the make command
  line (upstream hardcodes `gcc-ar`/`gcc-ranlib`).
- `package()` copies artifacts directly; upstream `make install` is skipped
  because it renders the man page through `go-md2man` (a Go tool).
- See `2.13/notes.md` for the full analysis and verification evidence.
