# eta 1.0.1 adaptation notes

## Package identity

- Conan package: `eta/1.0.1`
- Upstream: https://github.com/aioobe/eta — "Generic tool for monitoring ETA
  and progress of an arbitrary process"
- Upstream tag: `v1.0.1` (the only tag in the upstream repository)
- Conan package version matches the upstream version exactly; no R37
  increment needed as `eta/1.0.1` has not been published before.
- License: GPL-3.0-or-later (upstream LICENSE, bundled into `licenses/`).
- Package type: application (a single executable, no library product).

## W0 dependency conclusion

- Runtime dependencies: none beyond a libc (OHOS musl) and `/bin/sh` for
  `popen()` at runtime.
- Conan package dependencies: none.
- Build-only dependencies: `make` and a C compiler (provided by the CI
  runner / Conan toolchain).
- Test dependencies: none upstream; the consumer test needs `bash`, `grep`,
  `echo`, `true` on the target device.
- No dependency split required; no blocking missing dependency.

## Source audit (W1)

- Official tag archive
  `https://github.com/aioobe/eta/archive/refs/tags/v1.0.1.tar.gz`
  (format identifiable by the `.tar.gz` suffix; single root directory
  `eta-1.0.1/`, so `strip_root=True`).
- SHA256:
  `ccd41559dc12527d925ef32e22cd2c1e79428f3ec7a620ac9a74ed6be028d2e6`
- ~800 lines of C across `src/*.c|*.h`; plain Makefile (`CC = gcc`,
  `CFLAGS ?= -Wall`, no configure step, `mkdir -p obj` per object).
- The Makefile's `CC = gcc` is overridden on the command line
  (`make CC="<compiler>" -j1`) without patching; the OHOS cross command
  carries `--target`/`--sysroot` inside the compiler string.
- Upstream has NO test suite: no `test/` directory and no
  `test`/`check` Makefile target. Verification therefore rests on the
  consumer test_package plus the compile-time cross-check.

### Portability findings

- `src/eta.c` uses `WEXITSTATUS` without including `<sys/wait.h>`. It still
  compiles on glibc and on the OHOS musl sysroot only because both expose
  the macro transitively through `<stdlib.h>` (verified: the OHOS sysroot's
  `stdlib.h` defines `WEXITSTATUS` directly, which vanilla musl does not).
  The recipe adds `#include <sys/wait.h>` via `replace_in_file` so the
  source no longer depends on a libc-specific quirk (knowledge E336
  pattern: include the header that owns the API).
- Runtime dependency on `popen()`: musl hardcodes `/bin/sh` as the shell.
  If a target device lacks `/bin/sh`, eta cannot run its progress command.
  To be confirmed in the device round; not a build blocker.
- `CLOCK_MONOTONIC_RAW` and `TIOCGWINSZ` are exposed unconditionally by
  OHOS musl; no other glibc assumptions found (no pthread, no `/tmp`
  writes, no fork/exec beyond `popen`).

## Recipe decisions (W2/W3)

- `package_type = "application"`; `validate()` restricts to OHOS aarch64
  like other application packages.
- Source URL and SHA256 are defined directly in `conanfile.py` and no
  `conandata.yml` is shipped, avoiding the CI conandata.yml pre-download
  `BUILD_DIR` defect (same approach as the xmodem adaptation).
- One-line source patch (the `<sys/wait.h>` include) is applied with
  `replace_in_file` in `build()`; no conandata patches machinery needed.
- After `make`, the binary is signed with `binary-sign-tool` when building
  for OHOS (unsigned ELFs will not execute on device), same helper as
  acme/abbtr.
- Packaging: `bin/eta`, `licenses/LICENSE`, `share/man/man1/eta.1`,
  `share/eta/doc/README.md`. `package_info()` sets `bindirs = ["bin"]` and
  clears include/lib dirs (application package).
- test_package runs the installed binary through the device bash wrapper
  (`VirtualRunEnv` + `can_run` gate), with 16 deterministic assertions:
  `--help`, single-sample completion (`100%` / `Done`), `-w`, `-d -s`,
  `-i 1` acceptance, `-i 0` rejection, "no number in output" exit 3, and
  no-args exit 1. Every functional case completes on the first progress
  sample, so no test performs a `sleep` (upstream rejects `-i 0`).

## Local verification (W4)

- Source archive SHA256 re-verified locally (matches the recipe).
- OHOS cross compile (DevEco SDK clang 15.0.4,
  `--target=aarch64-linux-ohos --sysroot=<SDK>/sysroot`, `-Wall -Isrc`,
  all five `src/*.c`, then link):
  - builds and links cleanly; result is `ELF 64-bit LSB pie executable,
    ARM aarch64, ... interpreter /lib/ld-musl-aarch64.so.1`
    (`llvm-readelf -h`: ELF64 / DYN / AArch64).
  - only upstream-style deprecation warnings (empty-parameter prototypes),
    no errors.
  - unpatched source also compiles against the OHOS sysroot (see finding
    above); the include patch is kept for POSIX conformance and vanilla
    musl robustness, and was verified to apply and compile.
- `python -m py_compile` passes for both `conanfile.py` files.
- `sh -n` passes for `test_package/test.sh`.
- YAML structure check passes for `manifest.yaml` and
  `test_package/MANIFEST.yml`.
- Boundary check: changes limited to `archives/e/eta/1.0.1/`.
- `conan create` was NOT executed locally: Conan is not installed on this
  Windows host. The cross compile above replicates the recipe build
  commands (same compiler, sysroot, flags, and the patched source), but it
  is not a Conan invocation; recorded as such.

## Device shadow CI (W5) — executed

- Ran through the isolated-job runner (single-package queue with the device
  global lock; lock wait 0 seconds).
- Result: exit code 0.
- Gates: `L0_RESULT=pass`, `L1_RESULT=pass` (test_package executed, including
  the destructive negative re-check), `L2_RESULT=pass: eta --help OK`
  (the packaged binary really executes on device), `L4_RESULT=pass`,
  `L5_RESULT=pass: bin/ has content`.
- Consumer test on device: `test eta 1.0.1: 16/16 checks PASS`, 0 failed.
- Build on device: `make CC="<OHOS clang>" -j1` — clean compile, only the
  upstream empty-prototype deprecation warnings; the OHOS signing step
  (binary-sign-tool self-sign) executed on the packaged binary.
- `/bin/sh` confirmed present on the device, and the functional checks
  (`eta 5 echo 10`) passing proves the `popen()` path works end to end —
  the runtime risk noted above is resolved.
- No device-specific information is recorded in this repository per the
  security rules; run logs stay in the on-device job directory.

## Test inventory summary

- Upstream collected cases: 0 (no upstream test suite).
- Upstream cases executed: 0.
- test_package assertions: 16 (all local-design consumer checks).
- Skipped for platform reasons: 0.
- Device execution: 16/16 passed (shadow CI exit code 0).
