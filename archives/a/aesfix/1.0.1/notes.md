# aesfix 1.0.1 HarmonyOS adaptation notes

## Scope

- Worktree: `D:\harmonyos\worktrees\aesfix`
- Branch: `feat/aesfix-1.0.1`
- Archive path: `archives/a/aesfix/1.0.1`
- Issue: [#1843](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1843)

## W0 dependency check

aesfix 1.0.1 has no third-party build dependencies and the recipe declares no Conan requirements.

This round did not need dependency-library split-out work.

## Source and build system analysis

- Upstream project: AESFix 1.0.1 by Nadia Heninger and J. Alex Halderman.
- Homepage: `http://citp.princeton.edu/memory/`
- Source tarball used for reproducibility: `https://deb.debian.org/debian/pool/main/a/aesfix/aesfix_1.0.1.orig.tar.gz`
- sha256: `7b177e876caee6aae48f0123102f11df6594a738483f9a47f2c76fe81cc045d4`
- License: BSD-3-Clause style license in upstream `LICENSE`.
- Build system: plain Makefile.
- Output: one CLI binary, `aesfix`.

Upstream files:

```text
aesfix.cpp
errvect.cpp
errvect.h
aes.h
Makefile
README
LICENSE
samples/sched.100
samples/sched.120
samples/sched.140
samples/sched.160
```

The upstream Makefile only has `all`, `aesfix`, and `clean`; it does not provide an install target or upstream test target. The recipe builds with `make -j1`, passes `CXX` from Conan `tools.build:compiler_executables`, and packages the binary, README, license, and sample schedules manually.

## Test strategy

`aesfix` is a CLI tool, not a linkable library. The consumer test executes the packaged `bin/aesfix` against the packaged `share/aesfix/samples/sched.100`.

Important upstream behavior: when a corrected key schedule is found, `aesfix` prints it and calls `exit(1)`. The test treats exit code 1 as the expected successful sample behavior and asserts:

- output contains `corrected key schedule`
- output contains the expected first corrected row `91287ACD F26EC559 82DC89D3 6C7111E6`

This keeps the test tied to the real packaged CLI and sample data.

## Local verification completed

- Created isolated worktree from `origin/main`.
- Confirmed no existing `aesfix` files in `build_in_harmonyos`; issue was later provided by the user as #1843.
- Added software-level command metadata in `archives/a/aesfix/commands.json`.
- `python -m json.tool archives/a/aesfix/commands.json` passed.
- Downloaded the source tarball locally.
- Verified sha256: `7b177e876caee6aae48f0123102f11df6594a738483f9a47f2c76fe81cc045d4`.
- Inspected source, license, Makefile, README, and samples.
- Built a temporary Windows smoke binary with MSVC and ran `samples/sched.100`.
- MSVC smoke result: exit code 1 by upstream design, output included `corrected key schedule` and the expected corrected first row.
- `python -B -m py_compile` passed for `conanfile.py` and `test_package/conanfile.py`.
- `conan inspect archives/a/aesfix/1.0.1` passed.
- `conan export archives/a/aesfix/1.0.1 --user=ohpcd --channel=stable` passed.
- `conan source archives/a/aesfix/1.0.1` passed. Conan 2.29 ran `source()` in the recipe path, so the generated upstream source files were cleaned before handoff.
- `git diff --check -- archives/a/aesfix/1.0.1` passed.

Local compile limitations:

- Host MinGW `g++` is incomplete: it fails to include its own C++ standard library header `bits/stl_iterator.h`.
- Host `cl.exe` needed `vcvars64.bat`; after initializing the VS environment, the temporary MSVC smoke built with warnings only.
- `conan download aesfix/1.0.1@ohpcd/stable -r=ohpcd --only-recipe` failed locally with `system acceleration policy not enabled`.
- An earlier queued runner `/storage/Users/currentUser/ohos-test-runs/codex-aesfix-conan-1.0.1-20260804-200517-4107` failed before package build because the temporary launcher script had CRLF and zsh saw `ci/conan/build_and_test.sh^M`.

## OHOS single-package CI

Runner:

```text
/storage/Users/currentUser/ohos-test-runs/codex-aesfix-conan-1.0.1-20260805-022035-4960
```

Result:

```text
exit-code.txt: 0
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: aesfix version/help failed
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Build Summary: Total 1, Success 1, Failed 0
```

Notes:

- The runner waited 1031 seconds for the global device lock, acquired it, and completed with `rc=0`.
- `conan create` built and packaged `bin/aesfix` plus sample schedules.
- `test_package` executed the packaged `aesfix` binary against packaged `samples/sched.100`.
- The sample produced `corrected key schedule` and the expected first row `91287ACD F26EC559 82DC89D3 6C7111E6`.
- L2 skip is non-blocking because upstream `aesfix` has no standard `--help` or `--version` path; it only accepts `aesfix SCHEDULE-FILE`.

## Next verification commands

Single-package CI:

```sh
CI_PACKAGES="archives/a/aesfix/1.0.1" zsh ci/conan/build_and_test.sh
```

Shadow CI:

```sh
/path/to/run-ohos-shadow-ci.sh archives/a/aesfix/1.0.1
```

Manual Conan smoke on an OHOS worker:

```sh
cd archives/a/aesfix/1.0.1
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```
