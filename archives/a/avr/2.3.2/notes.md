# avr 2.3.2 HarmonyOS adaptation notes

## Status

- Branch: `feat/avr-2.3.2`
- Package path: `archives/a/avr/2.3.2`
- Upstream: AVR-LibC 2.3.2 (`avrdudes/avr-libc`)
- Current state: recipe, package build and consumer test are complete. Local
  static checks passed. Post-merge true-device shadow CI passed in
  `shadow-ci-r17-fast-probe-silent-jobs14` with L0/L1/L4/L5 passing and L2
  skipped only for the non-blocking `avr-man --version/--help` smoke check.

## Package boundary

This package is an AVR target sysroot package, not a native OHOS runtime
library. It packages AVR-LibC headers, startup objects and static archives for
AVR microcontrollers. The Conan package intentionally leaves native
`cpp_info.includedirs`, `cpp_info.libdirs`, `cpp_info.libs` and
`cpp_info.bindirs` empty so OHOS consumers do not accidentally link AVR objects
into native AArch64 binaries.

The build requires the AVR cross-toolchain chain:

```text
avr-binutils/2.43.1 -> avr-gcc-bootstrap/14.2.0 -> avr/2.3.2
```

The current PR must not include dependency recipes. After the dependency merge,
shadow CI resolves `avr-gcc-bootstrap/14.2.0` and the other build requirements
from the configured Conan cache/remote chain.

## Build strategy

- Use Autotools with upstream `bootstrap`.
- Configure with `--host=avr`.
- Disable documentation outputs.
- On OHOS, drive Autoconf/Automake through packaged Perl/M4 scripts rather than
  relying on execute bits in HMDFS.
- Patch generated `config.sub` at build time so `aarch64-linux-ohos` is
  accepted as a build triplet.
- Patch generated configure text in-place to avoid Autoconf `umask 077`
  temporary directories on HMDFS.
- Patch generated configure calls to run `devtools/mcu-to-avr-name.sh` through
  `sh`, avoiding HMDFS execute-bit failures.
- Build the complete AVR device/multilib tree with a capped default `-j14`.
  A `-j20` retry reached the device-library stage faster but exhausted true
  device memory, while `-j12` remained too slow for the 3600s shadow CI window.
  The `-j14` cap passed on the true device and can still be overridden through
  `tools.build:jobs`.
- Use upstream silent make output (`V=0`) to reduce true-device log I/O.
- Replace per-MCU empty compile probes with `avr-gcc -mmcu=<mcu>
  -print-multi-directory`; keep the real header compile checks, and skip only
  the asm-only devices for those header checks.

## Test strategy

Full runtime execution needs an AVR simulator such as `avrtest` or `simulavr`,
which is optional and not part of this PR. The GitHub tag tree contains
`tests/simulate`, but the official `avr-libc-2.3.2.tar.bz2` release archive used
by the package does not include that directory. The recipe now runs the upstream
compile/link test set only when `tests/simulate` is present and otherwise logs a
skip reason. Adding a second GitHub tag download for tests was avoided because
GitHub connectivity from both the Windows host and true device was unreliable in
this session.

The consumer `test_package` builds an ATmega328P ELF with the packaged CRT,
`libc.a`, `libm.a` and device library. It verifies the output is AVR
architecture and confirms linked `memcpy`, `strlen` and `sin` symbols.

## Validation on 2026-08-27

Completed locally on the Windows-side worktree:

- AST parse passed for `conanfile.py` and `test_package/conanfile.py`.
- YAML parse passed for `conandata.yml`, `manifest.yaml` and
  `test_package/MANIFEST.yml`.
- `git diff --check -- archives/a/avr/2.3.2` passed.
- GitHub API source-tree inventory completed without downloading the full
  archive.
- `tests/simulate` absence in the release tarball is handled by the recipe.

Completed on true device `10.62.220.52:2222` in isolated job
`/storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2`:

- Synced only `archives/a/avr/2.3.2`; transfer tar SHA256 was checked before
  extraction and matched on both sides.
- Latest main-side shadow CI front gates passed after the dependency merge:
  L0, KC and JC passed on
  `/storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2/repo/build_in_harmonyos-main-20260827`.
- `conan create` reached a full `make -j12` build of the AVR device/multilib
  tree in run
  `codex-avr-avr-2.3.2-codex-20260825-r2-shadow-ci-r8-jobs12-20260827-101940-25742`,
  then failed because `tests/simulate` was absent from the release archive
  before the skip guard was added.
- `shadow-ci-r9-jobs20-missing-simtests` confirmed the skip guard but failed
  during device library build with `avr-gcc: ... cc1: posix_spawn: Out of
  memory`.
- `shadow-ci-r10-jobs12-skip-missing-simtests` started too soon after r9 and
  failed in `bootstrap` with `can't fork - try again`.
- r12 confirmed the full `make -j12` build but hit the 3600s timeout during
  serial install.
- r13 added parallel install, but clean `make -j12` still timed out before
  install.
- r15 validated the fast-probe path and exposed an asm-only MCU edge case,
  which was fixed by preserving the upstream header-compile skip for asm-only
  devices.
- `shadow-ci-r17-fast-probe-silent-jobs14` passed:
  - `L0_RESULT=pass`
  - `L1_RESULT=pass`
  - `L2_RESULT=skip` because `avr-man --version/--help` failed as a
    non-blocking smoke check
  - `L4_RESULT=pass`
  - `L5_RESULT=pass`
  - build summary: `Success: 1`, `Failed: 0`, `Pass rate: 100.0%`
  - `test_package` compiled and linked the ATmega328P ELF and verified AVR
    architecture plus `memcpy`, `strlen` and `sin` evidence.

## Known gaps and blockers

- The dependency merge cleared the previous `avr-gcc-bootstrap/14.2.0` L0/R36
  blocker for this package.
- No current blocker for this package.
- AVR simulator execution is still not covered because `avrtest`/`simulavr` is
  optional and not part of this PR; the packaged consumer compile/link path is
  covered by `test_package`.

## Next commands

Official shadow CI reproduction:

```sh
zsh ci/conan/setup.sh
CI_PACKAGES="archives/a/avr/2.3.2" zsh ci/conan/build_and_test.sh "archives/a/avr/2.3.2"
```

Supplemental direct build on the prepared isolated job:

```sh
. /storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2/env.sh
cd "$CI_REPO_ROOT"
conan create archives/a/avr/2.3.2 -pr:a=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
