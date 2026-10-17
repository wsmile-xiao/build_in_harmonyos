# Local preflight: avr 2.3.2

- Date: 2026-08-27
- Worktree: `D:\harmonyos\worktrees\avr`
- Branch: `feat/avr-2.3.2`

## Source

- Project `search-url` guessed legacy `waterlan.home.xs4all.nl` URLs, but they
  returned HTML 404 content and were rejected.
- GitHub API confirms release `AVR-LibC 2.3.2 release`, tag
  `avr-libc-2_3_2-release`.
- Release asset:
  `https://github.com/avrdudes/avr-libc/releases/download/avr-libc-2_3_2-release/avr-libc-2.3.2.tar.bz2`
- Release asset SHA256:
  `92eb253d30cec94f2861a82d40d0b17ad79c0d95fce32b74ffccc26a70afb150`
- Shadow CI downloaded the release asset through the CI mirror fallback
  (`gh-proxy.com`) and verified the source during `conan create`.

## Build-system analysis

- GitHub API tree for tag `avr-libc-2_3_2-release` was retrieved with
  `truncated=False`.
- Root build entries present in the tag tree include `bootstrap`,
  `configure.ac`, `Makefile.am`, `devtools/configure`,
  `tests/simulate/runtest.sh` and `tests/simulate/run-avrtest.sh`.
- The official `avr-libc-2.3.2.tar.bz2` release asset used by Conan does not
  include `tests/simulate`; a true-device source tree inspection after r8 found
  no `tests` or `simulate` directory.
- The recipe now treats `tests/simulate` as optional: run the upstream
  compile/link test set if it exists, otherwise log a skip reason and proceed
  to package plus `test_package`.

The prepared recipe follows the AVR-LibC adaptation flow:

- Build system: Autotools with upstream `bootstrap`.
- Host: Linux/OHOS build host.
- Target: AVR, configured with `--host=avr`.
- Product: AVR target headers, CRT objects and static archives under `avr/`;
  no native OHOS include/lib/bin surface is exposed through `cpp_info`.
- Required AVR target tools are resolved only from Conan `tool_requires`.
- OHOS-specific runtime patches are applied in the recipe for `config.sub`,
  HMDFS execute-bit issues and Autoconf temporary directory creation.

## Local validation

Completed:

- Recipe and consumer-test files prepared under `archives/a/avr/2.3.2`.
- `test_package` compiles and links an ATmega328P consumer against packaged
  CRT, `libc.a`, `libm.a` and device library, then checks AVR architecture and
  `memcpy`, `strlen`, `sin` symbols.
- AST parse passed for `conanfile.py` and `test_package/conanfile.py`.
- YAML parse check passed for `conandata.yml`, `manifest.yaml` and
  `test_package/MANIFEST.yml`.
- `git diff --check -- archives/a/avr/2.3.2` passed.

## True-device validation

Prepared isolated job:

- Job base:
  `/storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2`
- Latest-main repo:
  `/storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2/repo/build_in_harmonyos-main-20260827`
- Conan home:
  `/storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2/conan-home`
- Last synced target-dir tar SHA256:
  `f99ec955afe3002b4cc171233acb0b83cc6d0546c7de5a704bf5e161fee788e8`

Completed after dependency merge:

- Latest-main L0/KC/JC front gates passed.
- `avr-gcc-bootstrap/14.2.0`, `avr-binutils/2.43.1`, `autoconf/2.72`,
  `automake/1.18`, `m4/1.4.19` and `perl/5.42.2` resolved from cache/remote.
- `shadow-ci-r8-jobs12` completed full AVR-LibC build and then failed only
  because the old recipe attempted to run missing `tests/simulate`.
- Recipe updated to skip missing release-archive simulate tests.
- `shadow-ci-r9-jobs20-missing-simtests` proved `-j20` is unsafe on this true
  device: `avr-gcc` failed to spawn `cc1` with `Out of memory`.
- `shadow-ci-r12-jobs12-after-device-recovery` completed the full `make -j12`
  build but timed out in the serial install stage.
- `shadow-ci-r13-install-parallel-jobs12` showed that parallel install alone is
  not enough; a clean `make -j12` build still exceeded the 3600s CI window.
- The recipe now shortens configure by replacing per-MCU empty compile probes
  with `avr-gcc -mmcu=<mcu> -print-multi-directory`, while preserving real
  header compile checks and the upstream asm-only MCU skip for those checks.
- The recipe now uses `V=0` and a default `-j14` cap for build/install. `-j14`
  passed on this true device; `tools.build:jobs` can still override it.
- `shadow-ci-r17-fast-probe-silent-jobs14` passed end-to-end:
  `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=skip` for the non-blocking
  `avr-man --version/--help` smoke check, `L4_RESULT=pass`,
  `L5_RESULT=pass`, build summary `Success: 1`, `Failed: 0`,
  `Pass rate: 100.0%`.
- `test_package` compiled and linked an ATmega328P ELF using the packaged CRT,
  `libc.a`, `libm.a` and `libatmega328p.a`, then verified AVR architecture and
  linked `memcpy`, `strlen` and `sin` evidence.

## Current blocker

None for this package. AVR simulator execution remains outside this PR because
`avrtest`/`simulavr` are optional and not adapted here.

## Next true-device/shadow CI command

Reproduce the passing shadow CI run:

```sh
cd /storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2/repo/build_in_harmonyos-main-20260827
zsh ci/conan/setup.sh
CI_PACKAGES="archives/a/avr/2.3.2" zsh ci/conan/build_and_test.sh "archives/a/avr/2.3.2"
```

Supplemental direct build command:

```sh
. /storage/Users/currentUser/ohos-users/codex/avr-2.3.2-codex-20260825-r2/env.sh
cd "$CI_REPO_ROOT"
conan create archives/a/avr/2.3.2 -pr:a=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
