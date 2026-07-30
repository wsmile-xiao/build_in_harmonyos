# nextvi 7.0

## Summary

- Upstream source: https://github.com/kyx0r/nextvi/archive/refs/tags/7.0.tar.gz
- SHA256: `2b4b79f79c504af206c0a7fb7d1d75edf45a176ba1531b651b2519e9126b11c3`
- Conan ref: `nextvi/7.0` for Conan version validity; task version: `nextvi/7`.
- Dependencies: none beyond POSIX libc/terminal APIs.
- Build output: `bin/vi`.

## Adaptation Notes

Upstream `Makefile` builds the editor with a direct `c99` invocation:

```text
${CC} ${CFLAGS} -o vi vi.c
```

The Conan recipe preserves that model but obtains the C compiler from the Conan
profile through `tools.build:compiler_executables`, which is required for OHOS
cross builds. Direct compiler invocations also need the profile-provided
`tools.build:cflags` and `tools.build:exelinkflags`; without those flags OHOS
clang does not receive the sysroot and fails on standard headers such as
`ctype.h`. The task version is `7`; the upstream release tag is `7.0`.

Windows/MinGW is not used as a compile probe for this package because nextvi
uses POSIX terminal APIs (`termios`, `ioctl`, `poll`, `fork`/`exec` paths) that
are expected on OHOS/Linux but not in the Windows local profile.

Upstream `test.sh` is the official release test suite and contains 250 checks.
It hardcodes `/tmp` for temporary files and `VI=./vi` for the editor under test.
On OHOS the recipe runs a build-directory copy of `test.sh`, rewrites the two
temporary path prefixes to a writable Conan build directory, and points `VI` at
the just-built editor binary. The upstream assertions themselves are unchanged.

## 2026-07-28 Local Verification

- `py_compile` for recipe and test package: PASS.
- `conan inspect archives/n/nextvi/7.0`: PASS.
- `conan export archives/n/nextvi/7.0`: PASS with exported ref `nextvi/7.0`.

## 2026-07-30 OHOS Real Device Verification

- SSH port: old port `56267`.
- Conan job: `/storage/Users/currentUser/ohos-users/codex-a/nextvi-7-oldport-r1`.
- Runner command used `--mode heavy` and `--try-lock`.
- Final `conan create + upstream test.sh + test_package`: PASS.
  - run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-nextvi-nextvi-7-conan-r6-oldport-upstream-in-build-20260730-053111-7582`
  - profile: `ohos-aarch64-current`
  - full ref: `nextvi/7.0#d250cd421832f5670d3b1cba988f119a:6b129b068851896169fae42d399fa922d239ce8a#5861f6793785b805ffa4d2abdfa5bca8`
  - L0/L1/L4/L5: pass.
  - L2: skip, because `vi` has no conventional `--version`/`--help`; `-?` prints usage and exits 1 by upstream behavior.
- Upstream tests:
  - `test.sh` in the release source contains 250 checks.
  - Integrated recipe run result: `250 passed, 0 failed`.
  - Standalone confirmation run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-nextvi-nextvi-7-upstream-test-r4-package-vi-and-tmp-20260730-052827-5258`.
- Earlier true-device failures before r6:
  - r2 failed L0 because `test_package/` had no standalone test source file; fixed by adding `test_nextvi.py`.
  - r4 failed compiling `vi.c` because direct clang invocation did not include profile sysroot flags; fixed by merging `tools.build:cflags`/`tools.build:exelinkflags`.
  - Upstream test r1/r2/r3 exposed harness issues: `/tmp` is read-only on the worker and upstream `test.sh` hardcodes `VI=./vi` while the Conan source cache does not contain the package binary.
