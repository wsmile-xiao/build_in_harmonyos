# Shadow CI report: aicommit2 2.8.0

Date: 2026-08-21
Shadow CI: `29189`
Device: provided HarmonyOS aarch64 worker (address withheld)
Runner: `ohos-test-runner.sh`
RUN_DIR: isolated single-package directory (withheld)

The isolated runner acquired the global device lock and invoked:

```text
zsh ci/conan/build_and_test.sh archives/a/aicommit2/2.8.0
```

Result:

- `Total: 1`
- L0: pass
- L1: pass
- L4: pass
- L5: pass
- Source download and checksum: pass
- Conan profile: `OHOS/armv8`, Conan 2.29.1
- Conan create: pass
- Conan `test_package`: pass
- Package success: `1/1`
- `ci-metadata.json`: generated
- Exit code: `0`

L2 is a non-blocking skip because HMDFS denies direct execution of the cached
launcher. The consumer test invokes the real package-owned launcher through
`sh` with the HNP Node.js runtime and passes. The packaged npm runtime tree is
kept under `res/aicommit2.tar.gz`, so nested dependency directories do not
produce false native-artifact findings in L5.

No device address, account, key path, or worker-local run path is retained in
this public report.
