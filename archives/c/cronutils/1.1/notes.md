# cronutils 1.1 adaptation notes

## Status

- Conan reference: `cronutils/1.1`
- Branch: `feat/cronutils-1.1`
- Worktree: `D:\harmonyos\worktrees\cronutils`
- Current stage: W0-W5 completed; ARM64 OHOS cross-compile, Conan create/package, and device consumer test passed
- Device/shadow CI: passed on 2026-09-11
- Issue tracking: intentionally omitted for this round

## W0 dependency check

cronutils 1.1 has no third-party runtime, build, or test dependencies. It is a
small C command-line utility set using POSIX libc APIs:

- `runalarm`: terminates a subprocess group after a timeout.
- `runlock`: serializes a command with an advisory file lock.
- `runstat`: records exit status, wall time, resource usage, and optional
  collectd output.

The package does not declare Conan dependencies. The target must provide the
POSIX process, signal, file-lock, time, and syslog APIs exposed by its libc.

## Source and build audit

The fixed source archive is the Debian Snapshot copy of the upstream 1.1
release:

- URL:
  `https://snapshot.debian.org/archive/debian/20110723T212944Z/pool/main/c/cronutils/cronutils_1.1.orig.tar.gz`
- SHA256:
  `28a5bbba67a1977be553aacc0b4087b61fef83857f8d7703b9bb823c07454035`
- Archive format: tar.gz
- Upstream identity: `cronutils-1.1`
- License: Apache-2.0

The archive has no configure script, CMake project, or automated test suite.
The raw Makefile defines three direct executable targets. The Conan recipe
reproduces those target/source mappings with direct clang invocations, which
keeps the package independent of a host `make` executable.

The Debian 1.1-3 source patch was reviewed but not copied wholesale. Its
relevant portability change is applied in `build()` by inserting the guarded
`HOST_NAME_MAX` fallback in `runstat.c`. Its linker-order change is represented
by passing an empty linker flag and explicit library arguments to clang. The
recipe also initializes `runlock`'s status variable so the OHOS
clang warning about an indeterminate return value is removed.

## HarmonyOS build decisions

1. Use the clang path from `tools.build:compiler_executables`.
2. Use `_XOPEN_SOURCE=700` for the POSIX declarations used by the old source;
   `runstat.c` retains its own `_GNU_SOURCE` definition for `dprintf()`.
3. Use GNU ld at `/data/service/hnp/bin/ld` on OHOS, matching the worker
   toolchain conventions used by other executable packages. Local DevEco
   builds can set `user.ohos:ld_path` to the SDK's `ld.lld.exe`.
4. Do not link standalone `-lrt` on OHOS. The local knowledge base records that
   HarmonyOS libc provides `clock_gettime`; Linux keeps `-lrt` for compatibility
   with older Linux libc environments.
5. Install to `bin/` and `share/man/man1/` with Conan file copying, matching
   the upstream install layout without requiring host `make`.
6. Avoid the upstream default `/tmp/cronutils-<user>` path in the consumer test:
   `runlock` and `runstat` receive explicit writable `-f` paths.
7. Self-sign the three packaged OHOS ELF files with `llvm-objcopy` and
   `binary-sign-tool -selfSign 1`; `chmod 755` alone is insufficient for
   execution from the Conan package cache.

## Test package

`test_package/test_cronutils.py` performs 18 consumer assertions:

- all three installed commands exist;
- each `-h` path returns success and prints usage;
- `runalarm` forwards a child exit code;
- `runalarm -t 1` returns the timeout status for a sleeping child;
- two `runlock` consumers demonstrate mutual exclusion and the expected
  `EX_CANTCREAT` result for the blocked process;
- `runstat -f` returns the child status and writes `exit_status` and
  `elapsed_time` CSV records.

The test uses absolute paths and Python `subprocess` calls, avoiding `/bin/sh`
and PATH lookup assumptions in the test harness. The explicit statistics and
lock paths also avoid the read-only `/tmp` behavior documented for HarmonyOS.

## Local verification

Completed on 2026-09-11:

- worktree created from refreshed `origin/main`;
- source archive downloaded from Debian Snapshot;
- source archive SHA256 matched the `.dsc` checksum:
  `28a5bbba67a1977be553aacc0b4087b61fef83857f8d7703b9bb823c07454035`;
- archive member list and Debian 1.1-3 packaging patches inspected;
- Python/Conan recipe and manifest files prepared.
- DevEco Studio BiSheng clang cross-compiled and linked all three AArch64 OHOS executables;
- `llvm-readelf` confirmed ELF64/AArch64, PIE/NOW, GNU_STACK, and libc-only dynamic dependency.
- Conan 2.12.0 `conan create` completed source, build, package, and cross-test setup;
  the runtime consumer test was skipped because the Windows host cannot execute OHOS ELF.
- The first device run built and packaged all three tools but failed at the first
  consumer execution with `PermissionError: [Errno 13]`, proving that the
  unsigned package artifacts could not execute on HarmonyOS.
- After adding package-time ELF signing, the isolated device run passed Conan
  create, test_package, and the L2 smoke checks.

Not executed on this Windows host:

- `conan inspect`: not run separately because `conan create` already evaluated and built the recipe;
- upstream tests: no upstream test target exists;
- installed consumer test: OHOS ELF binaries cannot execute on this Windows host;

## Device shadow CI

The isolated heavy runner completed on 2026-09-11 with the following evidence:

- L0 quality gate: passed, including R38 `commands.json`;
- Conan create/package: passed with the OHOS clang and linker profile;
- package-time signing: all three tools received a `.codesign` section;
- test_package: passed `18/18` assertions on the AArch64 HarmonyOS device;
- L1 test execution: passed;
- L2 smoke: `runalarm --help`, `runlock --help`, and `runstat --help` passed;
- L4: no upstream test target, so no upstream test was required;
- L5: package `bin/` artifact check passed;
- final shadow runner exit code: `0`.

## Next commands

For a future worker rerun, execute the package in an isolated heavy job:

```sh
CI_PACKAGES="archives/c/cronutils/1.1" zsh ci/conan/build_and_test.sh
```

For a direct isolated Conan create on an allocated OHOS worker:

```sh
cd archives/c/cronutils/1.1
conan create . --build=missing \
  -s:h os=OHOS -s:h arch=armv8 \
  -s:h compiler=clang -s:h compiler.version=15 \
  -s:h compiler.libcxx=libc++ -s:h build_type=Release \
  -s:b os=OHOS -s:b arch=armv8 \
  -s:b compiler=clang -s:b compiler.version=15 \
  -s:b compiler.libcxx=libc++ -s:b build_type=Release
```

The package recipe now performs the normal HarmonyOS signing step during
`package()` whenever the target OS is OHOS; a device rerun should verify the
signature output before executing `test_package`.

## R38 command metadata

The package produces three CLI commands, so the software-level
`archives/c/cronutils/commands.json` is included. It declares the `1.1`
reference and allows R38/L0k to recognize the package as a tool.

## Knowledge draft

The directly related path B candidate is recorded as a paired draft:

- `knowledge/DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing.md`
- `knowledge/DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing.kv`

It records the raw Makefile migration, OHOS POSIX/linker differences, the first
unsigned-ELF `PermissionError`, package-time signing fix, R38 command metadata,
and the final 18/18 device consumer evidence. It is marked as a verified draft
candidate only; formal numbering and B-class recognition remain a maintainer
review decision.
