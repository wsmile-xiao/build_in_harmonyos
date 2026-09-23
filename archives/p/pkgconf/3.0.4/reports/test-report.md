# pkgconf 3.0.4 test report

**Test date**: 2026-09-03
**Target**: OpenHarmony 6.0, arm64, Clang 15

## Result

- Build status: passed
- Upstream tests: 555/555 (100%)
- Added assertions: 26/26 (100%)

## Upstream inventory

| Inventory | Passed | Total |
| --- | ---: | ---: |
| API executables | 15 | 15 |
| Fixture files in 14 suites | 394 | 394 |
| Capability-gated OOM test | 1 | 1 |
| Parser corpus inputs | 128 | 128 |
| Solver corpus inputs | 3 | 3 |
| Missing-corpus negative test | 1 | 1 |
| Total | 555 | 555 |

The upstream suite ran twice from two independent trees and registered the
same 33 top-level Meson test names. The canonical map contains 394 unique
`(suite, fixture)` keys for this release: 390 real `PASS` terminals plus 4
`SKIP` terminals whose fixtures declare `SkipPlatforms: unix haiku lite`
(all four are Windows-oriented sysroot cases); failed official entries are
zero. The missing-corpus negative is bound to `EXPECTEDFAIL`, return code 1,
`REPLAYED_INPUTS=0`, and the missing-path stderr marker. The corpus runners
reported `REPLAYED_INPUTS=128` (127 `.pc` files in `tests/lib1/` plus one
in `tests/lib1/child-prefix/pkgconfig/`) and `REPLAYED_INPUTS=3`.

Direct command evidence from the packaged artifacts:

- `pkgconf --version` -> `3.0.4`
- `bomtool --version` -> `bomtool 3.0.4`
- `spdxtool --version` -> `spdxtool 3.0.4`
- `pccritic --version` -> `pccritic 3.0.4`
- `pkgconf --modversion pkgconf-fixture` -> `1.2.3`
- `pkgconf --cflags pkgconf-fixture` -> `-I/test/include`
- `pkgconf --libs pkgconf-fixture` -> `-L/test/lib -lpkgconf_fixture`
- `bomtool --creation-time=2026-09-03T00:00:00Z pkgconf-fixture` ->
  contains `SPDXVersion: SPDX-2.2` and `PackageName: pkgconf-fixture@1.2.3`
- `spdxtool --creation-time=2026-09-03T00:00:00Z pkgconf-fixture` ->
  JSON-LD context `https://spdx.org/rdf/3.0.1/spdx-context.jsonld`, exactly
  one `software_Package` named `pkgconf-fixture` version `1.2.3`
- `pccritic --quiet pkgconf-fixture.pc` -> `100/100 (A)`

## Conan package

- Package ID: `21b17f8b2bc0e9511e276e3d57a23893067cefe5`
- Consumer compile and link: passed (`CONSUMER_COMPILE_LINK_TESTS=1/1`);
  `test_pkgconf` printed `LIBPKGCONF_VERSION=30004`, `PATH_SPLIT_COUNT=2`,
  `API_ASSERTIONS=12`.
- Local CI: passed (1/1 package; L0, L1, L1b, L1c, L1e, L2, and L5 passed;
  L4's only warning is the scanner flagging `reallocarray` in the test-only
  overflow-safe shim patch, which introduces no dangerous call).
- CLI runtime assertions: 14/14 executed directly from the packaged
  commands on this device (see the command evidence above); inside
  `conan create` the OHOS-runtime branch reports
  `TARGET_RUNTIME_TESTS=NOT_RUN` only when the worker lacks the three
  signing tools (`llvm-objcopy`, `llvm-readelf`, `binary-sign-tool`).

## Artifact closure

- Commands: `pkgconf`, `bomtool`, `spdxtool`, `pccritic`
- Library: `lib/pkgconf/libpkgconf.a` (static only, R26)
- Headers: `include/pkgconf/libpkgconf/{libpkgconf.h,stdinc.h,iter.h,bsdstubs.h,libpkgconf-api.h}`
- Metadata: `lib/pkgconfig/libpkgconf.pc`, `share/aclocal/pkg.m4`
- No `pkg-config` alias (upstream 3.0.4 does not install one)

## Patch series

All seven portability patches reuse the validated 3.0.5 series. The two
patches that touch release-version-sensitive files (`0006-meson.build`,
`0007-tests-api-tmpfile`) were regenerated at 3.0.4 coordinates because the
3.0.5 release added two libc function probes (`getc_unlocked`, `mkdtemp`)
above the OOM section, shifting hunk line numbers. Verification: `git apply`
7/7 clean and the Conan patch engine (patch_ng, strip=0) 7/7 clean against
the pristine `pkgconf-3.0.4.tar.xz`; both patched trees are identical and
equal the tree that passed the complete upstream inventory above.
