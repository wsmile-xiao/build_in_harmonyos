# cloop 3.14.1.3-nmu1 test report

## Build

- Profile: `ci/conan/profiles/ohos-aarch64`
- Architecture: OHOS `armv8` / aarch64
- Compiler: clang 15.0.4 / libc++
- Command: `conan create archives/c/cloop/3.14.1.3-nmu1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --test-folder=test_package`
- Result: passed (fresh Conan cache rebuild)
- Packaged executables: `advfs`, `create_compressed_fs`, `extract_compressed_fs`

## Tests

| Category | Count | Passed | Result |
|---|---:|---:|---|
| Upstream `make check-local` target | 1 | 0 | Failed before functional assertions because the shipped target uses obsolete `advfs` syntax |
| HarmonyOS consumer test | 1 | 1 | Passed |

The consumer test was run from a package produced after deleting the cloop Conan cache. It compressed an 8192-byte input with a 65536-byte cloop block, extracted it, verified the original prefix, exact block length, and zero padding.

## Notes

The upstream test failure is reported honestly and is not counted as a passing test. No upstream test files were modified.
