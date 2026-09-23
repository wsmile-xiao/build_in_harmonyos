# APR 1.7.6.1 HarmonyOS validation (upstream 1.7.6)

## Build result

- Target: HarmonyOS PC, `os=OHOS`, `arch=armv8`
- Build system: autotools
- Compiler: clang/clang++
- Library build: passed
- Conan consumer `test_package`: passed (`test_apr` executed, `EXIT=0`)

## Upstream test result

The upstream suite contains 45 test modules. `make check` was executed separately on the OHOS device and did **not** pass:

| Test | Result | Reason |
|---|---|---|
| `testmutexscope` | exit 159 (`SIGSYS`) | proc mutex pshared syscall rejected by the OHOS sandbox/seccomp policy |
| `testdso` | 8/9 failed | OHOS `dlopen` does not support the libtool `.libs/mod_test.so` path |
| `testfile` | 4/61 failed | hardlink unsupported; errno `70014` differs from the upstream expectation |
| `testfilecopy` | 2/4 failed | OHOS file-copy API returns `ENOENT` for the upstream case |
| `testflock` | 2/3 failed | fork/exec launch is restricted and returns `ENOENT` |
| `testfnmatch` | 2/4 failed | OHOS libc returns a different `fnmatch` result |
| `testmmap` | crashed (`SIGSEGV`, exit 139) | OHOS mmap behavior differs after the expected return value `2` |

These are OHOS platform restrictions observed after successful compilation, not claimed APR defects. The Conan recipe intentionally builds the library and runs the consumer test without invoking the failing full `make check` target. Full details are in `BLOCKED.md` and `test_package/MANIFEST.yml`.

## Adaptation patches

- `0011-config.guess-harmonyos.patch`: map HarmonyOS aarch64 to `aarch64-unknown-linux-ohos`.
- `0012-config.guess-libc-ohos.patch`: add OHOS libc detection.
- `0013-config.sub-ohos.patch`: accept the `ohos-linux` triplet.
- `0014-configure-hmdfs-umask.patch`: use HMDFS-compatible temporary-directory umask.
