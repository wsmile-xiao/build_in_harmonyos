# APR 1.7.6.1 HarmonyOS adaptation

## Build environment

- Build system: autotools
- Target: HarmonyOS PC, `os=OHOS`, `arch=armv8`
- Compiler: clang/clang++
- Status: library and consumer test validated on device; upstream suite has an OHOS platform failure

## Adaptation

The recipe applies four focused patches:

- `0011-config.guess-harmonyos.patch`: recognizes `HarmonyOS` and maps aarch64 to `aarch64-unknown-linux-ohos`.
- `0012-config.guess-libc-ohos.patch`: adds OHOS libc detection for compiler-based config.guess paths.
- `0013-config.sub-ohos.patch`: accepts the `ohos-linux` triplet.
- `0014-configure-hmdfs-umask.patch`: changes temporary-directory creation from umask `077` to `022` for HMDFS compatibility.

## Dependencies

APR has no Conan runtime dependencies.

## Verification

```text
conan create archives/a/apr/1.7.6.1 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
EXIT=0
configure: aarch64-unknown-linux-ohos
test_package: test_apr built and executed
```

The upstream suite contains 45 test modules and is recorded for comparison, but is not counted as passed on OHOS. The device run identified platform failures after successful compilation: `testmutexscope` exited 159 (`SIGSYS`) because the proc-mutex pshared syscall is sandbox-rejected; `testall` exited 139 (`SIGSEGV`) with failures in `testdso` (8/9, `.libs` dlopen path), `testfile` (4/61, hardlink/errno semantics), `testfilecopy` (2/4, copy API), `testflock` (2/3, fork/exec), `testfnmatch` (2/4, libc result), and `testmmap` (crash after mmap return 2). The recipe therefore does not execute `make check`. The Conan consumer test remains the supported adaptation smoke test.
