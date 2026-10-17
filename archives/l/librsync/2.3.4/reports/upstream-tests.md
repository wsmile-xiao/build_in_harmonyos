# librsync 2.3.4 upstream test inventory

Source release:
`https://github.com/librsync/librsync/releases/download/v2.3.4/librsync-2.3.4.tar.gz`

The upstream CMake project always registers these seven library tests:

| Test | Source |
| --- | --- |
| `isprefix_test` | `tests/isprefix_test.c` |
| `netint_test` | `tests/netint_test.c` |
| `rollsum_test` | `tests/rollsum_test.c` |
| `rabinkarp_test` | `tests/rabinkarp_test.c` |
| `hashtable_test` | `tests/hashtable_test.c` |
| `checksum_test` | `tests/checksum_test.c` |
| `sumset_test` | `tests/sumset_test.c` |

The same CMake project conditionally registers eight `rdiff` command-line tests
only when `BUILD_RDIFF=ON`, which depends on `popt` being found:

| Test | Source |
| --- | --- |
| `rdiff_bad_option` | `tests/rdiff_bad_option.test` |
| `Help` | `tests/help.test` |
| `Mutate` | `tests/mutate.test` |
| `Signature` | `tests/signature.test` |
| `Sources` | `tests/sources.test` |
| `Triple` | `tests/triple.test` |
| `Delta` | `tests/delta.test` |
| `Changes` | `tests/changes.test` |

This package config enables `BUILD_RDIFF` and consumes the published
`popt/1.16#cca44e0c65c2ff043d329f27a068a956` Conan recipe from the `ohpcd`
remote. The repository tree still has an older partial `archives/p/popt/1.16`
archive, so dependency availability is recorded separately in
`dependency-resolution.md`. This package also consumes `perl/5.42.2` as a
build/test tool requirement for `tests/mutate.test`, so both the seven library
tests and the eight conditional `rdiff` command-line tests are registered and
executable.

## OHOS result

The OHOS PC runner run on port 33332 on 2026-08-04 executed the upstream CTest
suite during `conan create`:

```text
1/15 Test  #1: isprefix_test ....................   Passed
2/15 Test  #2: netint_test ......................   Passed
3/15 Test  #3: rollsum_test .....................   Passed
4/15 Test  #4: rabinkarp_test ...................   Passed
5/15 Test  #5: hashtable_test ...................   Passed
6/15 Test  #6: checksum_test ....................   Passed
7/15 Test  #7: sumset_test ......................   Passed
8/15 Test  #8: rdiff_bad_option .................   Passed
9/15 Test  #9: Help .............................   Passed
10/15 Test #10: Mutate ...........................   Passed
11/15 Test #11: Signature ........................   Passed
12/15 Test #12: Sources ..........................   Passed
13/15 Test #13: Triple ...........................   Passed
14/15 Test #14: Delta ............................   Passed
15/15 Test #15: Changes ..........................   Passed
100% tests passed, 0 tests failed out of 15
```

The Conan consumer test also passed:

```text
1/1 Test #1: test_librsync ....................   Passed
librsync librsync 2.3.4 ok
```
