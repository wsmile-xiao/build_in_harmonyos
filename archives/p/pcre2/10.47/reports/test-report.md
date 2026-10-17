# PCRE2 10.47 Test Report

Status: PASS

## Counted test inventory

| Scope | Inventory | Executed | Passed | Failed | Skipped |
|-------|----------:|---------:|-------:|-------:|--------:|
| Official upstream Automake entries | 4 | 4 | 4 | 0 | 0 |
| Added Conan consumer flows | 8 | 8 | 8 | 0 | 0 |
| **Counted tests** | **12** | **12** | **12** | **0** | **0** |

The six metadata-relocation checks passed `6/6`, but they are package
invariants rather than independent test cases and are not added to the test
count.

## Upstream inventory

`Makefile.am` registers four entries under the enabled 8/16/32-bit and JIT
configuration:

1. `pcre2posix_test`
2. `pcre2_jit_test`
3. `RunTest`
4. `RunGrepTest`

The exact OpenHarmony PC run executed `make -j1 check`. Automake reported
`TOTAL=4`, `PASS=4`, `SKIP=0`, `XFAIL=0`, `FAIL=0`, `XPASS=0`, and `ERROR=0`.
The source test files were not modified.

## Added consumer inventory

The Conan `test_package` executed eight independent flows:

1. PCRE2 8-bit API compile, JIT, match, offsets, and capture.
2. PCRE2 16-bit API compile, JIT, match, offsets, and capture.
3. PCRE2 32-bit API compile, JIT, match, offsets, and capture.
4. POSIX API compile, match, capture, non-match, and error handling.
5. An 8-bit consumer resolved through the installed pkg-config metadata.
6. Packaged `pcre2grep` exact-line matching.
7. Packaged `pcre2test -C` configuration and JIT capability reporting.
8. Packaged `pcre2-config` relocation and static-link flag resolution.

The first five flows ran through CTest with `--parallel 1`; the command and
metadata consumers ran from the same package revision and target snapshot.

## Exact-snapshot evidence

- Git HEAD: `89569e4e0774f39cca827f22b2f16a79115acb9e`
- Git tree: `5db01d22f15a6fc895d9c5972570965aa4fd8b2c`
- Fixed base: `807fa2c350480cb15271d1891f23b2b991916fd5`
- Device: `10.62.148.108:2222`
- Run ID: `pcre2-10.47-task3311-bootstrap-v1-r2-148108-w3-r66`
- Transaction SHA-256: `86285f520d720211d81b7d21cb77ca04828c99927bf80bd3a22da7efc27a269a`
- Runner exit: `0`
- Conan log SHA-256: `d5ce76b3c5ae033b2fa42b841ab8fab84bda06af59423a417b3f3be820cd04dd`
- CI result SHA-256: `2c2178dec7ab3117509979c2ffe2128e61bc77131dc6640b2deba4e3d49c7766`
- Recipe revision: `dbe7cf6a762bdc5bd059b6c819644f90`
- Package ID: `f23d5a9b1d537641c03c7814478a2fadb727650a`
- Package revision: `55cc37c3cf7622249796066edb894d9e`

The enclosing legacy `finish` command returned 1 only for post-run framework
warnings. The actual build/test runner returned 0; the result extractor and
independent readback audit bound that classification without changing the
historical log.

## Conclusion

PCRE2 10.47 passed the complete official upstream inventory and all declared
consumer flows on one OpenHarmony PC snapshot using single-job build and test
execution. No Conan, CNB, or other artifact-repository upload was performed.
