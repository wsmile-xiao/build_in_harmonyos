# Verification note

The OHOS device validation for the library build and `test_package/test_apr` is complete with `EXIT=0`. The upstream `make check` target was attempted separately and is not counted as passed because OHOS platform restrictions caused these failures:

| Test | Result | OHOS limitation |
|---|---|---|
| `testmutexscope` | exit 159 (`SIGSYS`) | proc mutex default mechanism triggers a sandbox/seccomp-rejected pshared-mutex syscall |
| `testall` / `testdso` | 8/9 failed | OHOS `dlopen` does not accept the libtool `.libs/mod_test.so` path |
| `testall` / `testfile` | 4/61 failed | hardlinks are unavailable and errno `70014` differs from the upstream expectation |
| `testall` / `testfilecopy` | 2/4 failed | OHOS file-copy API returns `ENOENT` for the upstream case |
| `testall` / `testflock` | 2/3 failed | fork/exec launch is restricted and returns `ENOENT` |
| `testall` / `testfnmatch` | 2/4 failed | OHOS libc returns a different `fnmatch` result for one case |
| `testall` / `testmmap` | crashed (`SIGSEGV`, exit 139) | mmap behavior differs after the expected return value is `2` |

The recipe intentionally does not run the failing full suite. These are platform constraints, not claimed APR defects. The local Windows environment cannot execute OHOS aarch64 binaries. To reproduce the supported package validation on an OHOS device:

```bash
conan create archives/a/apr/1.7.6.1 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```

The command builds APR and executes the consumer `test_apr` binary. Do not interpret it as a full upstream-suite pass.
