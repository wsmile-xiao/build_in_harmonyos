# Cifer 1.2.0 — Adaptation Notes

## Overview
- **Software**: cifer 1.2.0
- **Build System**: Raw Makefile (no autotools, no cmake)
- **Type**: CLI application (two binaries: `cifer` and `cifer-dict`)
- **Dependencies**: readline/8.3, ncurses/6.6

## Source
- Upstream: https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/cifer/cifer-1.2.0.tar.gz
- SHA256: `436816c1f9112b8b80cf974596095648d60ffd47eca8eb91fdeb19d3538ea793`

## Patches Applied
1. **0002-readline-static-link.patch** (via conandata): Added `LDFLAGS=-static` and `-ldl` to Makefile for R26 compliance.
2. **cifer-dict shebang fix** (applied in build() via load/save): OHOS has no `/bin/bash`; changed shebang from `#!/bin/bash` to `#!/bin/sh`. Also fixed `let OUTFILEN=$#-1` to POSIX `$(($# - 1))` and hardcoded `/tmp` paths to use `${TMPDIR:-/tmp}`.

Note: The cifer-dict patch (0001) is applied programmatically in `build()` because the conandata patch mechanism had reliability issues on the OHOS PC environment. The load/save approach in build() is more robust.

## Build Command
```bash
make CC={cc} CFLAGS='-I{readline_include} -I{ncurses_include}' \
  LINKLIBS='-lreadline -lncursesw -lformw -lmenuw -lpanelw -ldl' \
  LDFLAGS='-static -O2 -L{readline_lib} -L{ncurses_lib}' -j1
```

Note: ncurses/6.6 provides `libncursesw` (wide-char), not `libncurses`. Must link all related libs.

## Installation
- Binaries: `bin/cifer`, `bin/cifer-dict`
- Man pages: `share/man/man1/cifer.1`, `share/man/man1/cifer-dict.1`

## Tests
- No upstream tests exist (verified by source audit).
- test_package covers: binary existence and basic smoke test via `test.sh`.
- MANIFEST.yml declares `upstream_tests_exist: false` with audit justification.

## Known Limitations
- cifer requires interactive TTY for normal operation; test_package uses `-x` flag for immediate exit.
- No upstream test suite; only basic smoke test in test_package.

## Build Verification (HarmonyOS aarch64 真机)
- Environment: `ohos@c1.sermc.net` (aarch64, real OHOS kernel + HNP toolchain)
- Compiler: `/data/service/hnp/bin/clang` (clang-15)
- Conan: 2.30 (OHOS adaptation)
- Result: conan create PASSED (compile + test_package both passed)
  - cifer: PASS
  - cifer-dict: PASS
