# cimfomfa 21-361 test report

## Result

- Native Conan build and package: PASS (`macos-arm64`, Conan 2.29.1)
- Build-tool dependency: `automake/1.18` downloaded from the `ohpcd` registry
- Upstream registered tests: 0 (`make check` reports no registered tests)
- Upstream diagnostic programs compiled: 16/16
- Representative upstream programs executed: 9/9 PASS
- Installed-package consumer: PASS, 9/9 assertions
- HarmonyOS PC CI build #42369: PASS (recipe + upstream programs + consumer)
- HarmonyOS-specific test: 1 executable, 10 failure-checked assertions; pending
  execution in the next OHOS CI run

The native result establishes the upstream baseline, and build #42369 verifies
the recipe and consumer on the HarmonyOS worker.

## Upstream coverage

The upstream README states that cimfomfa has no unit test suite.
`src/trumpet/Makefile.am` defines 16 `noinst_PROGRAMS`, all of which are built
by the recipe. Nine deterministic or internally checked representatives are
also executed:

1. `cff_pagesize`
2. `cff_link`
3. `cff_bitpat`
4. `cff_let`
5. `cff_tst`
6. `cff_unit_ceilfloor`
7. `cff_optoid`
8. `cff_match`
9. `cff_read`

The remaining seven programs require interactive, bulk-data, or specialized
diagnostic inputs and are not registered upstream tests. They are compiled but
are not counted as executed or skipped tests.

## Consumer coverage

The C consumer links the packaged `libtingea.a` through the exported
`cimfomfa::cimfomfa` CMake target. Nine checked assertions cover `mcxTing`
allocation, length, content, append, and free behavior together with
duplicate-aware `mcxBsearchFloor` and `mcxBsearchCeil` results.

`test_harmonyos.c` is a separate HarmonyOS-specific consumer. It refuses to
compile without the OHOS and aarch64 target macros, checks the actual OHOS libc
page-size and UID values, and performs ten failure-checked assertions while
calling the packaged `mcxTing` and `mcxBsearchFloor`/`mcxBsearchCeil` APIs.

## Commands

```text
autoreconf -fi
../configure --prefix=<temporary-prefix>
make -j2
make check
make install
conan create archives/c/cimfomfa/21-361 -pr:h=macos-arm64 -pr:b=macos-arm64 --build=missing --user=ohpcd --channel=stable
```

PR #8929 build #42331 initially failed before compilation because the OHOS CI
image did not contain `aclocal`. The recipe now obtains `aclocal` and
`automake` from the published `automake/1.18` build requirement.

Build #42369 passed on the HarmonyOS worker after the Autotools and HMDFS fixes.
The new HarmonyOS-specific executable requires a fresh CI run after this change.

## Conclusion

The native build, package, upstream-program coverage, and installed-package
consumer pass, and build #42369 verifies the package on the HarmonyOS worker.
The added HarmonyOS-specific test awaits the next PR CI run.
