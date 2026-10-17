# minised 1.16

minised is the historic small-SED implementation originally written by Eric S.
Raymond and maintained by ExactCODE. It is a single command-line program built
from two C translation units (`sedcomp.c`, `sedexec.c`) by a plain `Makefile`,
with no configure script and no external dependency beyond libc.

## Build system analysis

The upstream `Makefile` is minimal and self-contained:

- `make` builds `sedcomp.o` + `sedexec.o` and links the `minised` binary.
- `make check` runs `tests/run`, a POSIX shell harness that feeds every
  `tests/*.sed` program through the freshly built `minised` and diffs the
  output against `tests/*.out`.
- `make install` uses the `install` coreutil to place the binary and man page.

It already supports `DESTDIR`/`PREFIX`, so it is cross-compile friendly out of
the box. No patching of source or build files was needed — the adaptation is
zero-patch.

## HarmonyOS adaptation

- **Toolchain**: `CC` is read from the Conan conf
  `tools.build:compiler_executables` (R33). The OHOS profile points this at the
  device clang; no host `gcc`/`g++` is ever invoked.
- **Build**: the native `make CC=clang -j1` is reused unchanged. The upstream
  `CFLAGS += -O1 -Wall -Wwrite-strings` stays in effect.
- **Upstream tests**: `make check` is executed in `build()` (L1). The
  `tests/run` harness iterates over all 68 `tests/*.sed` cases, feeding each
  through the built minised and diffing against `tests/*.out`. It uses `mktemp`
  and `$(<file)` redirection; both work under the OHOS `/bin/sh` when run from
  a writable build folder. Result: **68 cases — 66 passed, 1 expected-fail
  negative test (empty-lhs, no `.out`), 1 harness-artifact failure (w2)**.
  - `empty-lhs` is a *negative* test: it has no `.out` file and expects a
    non-zero exit (`s///` with empty LHS is an error). The harness reports
    "Failed (as expected)" — this is correct behavior, not a failure.
  - `w2` is a *harness artifact, not a minised bug*: `w2.sed` writes one line
    to `/dev/stderr` via the `w` command, but the harness captures with
    `> $tmp 2>&1` (merging streams), so the stderr line lands out-of-order vs
    `w2.out`. Verified directly: minised stdout alone matches `w2.out` minus
    the stderr line; minised stderr alone carries exactly that line. minised's
    stream routing is correct; only the harness's stream merge is wrong.
  - Note: the upstream `tests/run` harness does **not** `exit $errors`, so
    `make check` returns 0 even with the w2 "failure". This is an upstream
    harness limitation, unchanged by this adaptation (zero-patch).
- **Install**: `make install` is **not** used because OHOS does not ship the
  `install` coreutil (same situation as fakesteak). `package()` copies the
  built `minised` binary into `package/bin`, the `minised.1` man page into
  `share/man/man1`, and `LICENSE` into `licenses/` directly.

## Consumer test

`test_package/test_minised.sh` runs the packaged binary against real inputs
(no `--help`/`--version` assertions as the primary check):

1. **Substitution** (required example): `echo 'hello world' | s/world/OpenHarmony/`
   → `hello OpenHarmony`.
2. **Line deletion**: delete lines matching `/delete me/d` and `/^a$/d`.
3. **Simple regex**: `s/a*/x/g` on `aaab` → `xb`.
4. **Backreference**: `s/c/[&]/` on `cat` → `[c]at`.

All assertions pass on the OHOS aarch64 device.
