# libdbi-drivers 0.9.0 adaptation notes

## Scope

This recipe packages the upstream SQLite3 loadable driver for libdbi. The
release also contains optional drivers for MySQL, PostgreSQL, DB2, Firebird,
FreeTDS, Ingres, mSQL, and Oracle; those require database-specific client
libraries that are not part of this reproducible HarmonyOS package.

## Source integrity

- Upstream release: 0.9.0
- Source: `https://downloads.sourceforge.net/libdbi-drivers/libdbi-drivers-0.9.0.tar.gz`
- SHA256: `43d2eacd573a4faff296fa925dd97fbf2aedbf1ae35c6263478210c61004c854`

## Build configuration

The recipe uses the Conan `libdbi/0.9.0-r5` framework and `sqlite3/3.53.4`
static engine. It enables only `--with-sqlite3` and disables documentation.
The old `AC_CHECK_SQLITE3` macro uses `-lsqlite` when an explicit library
argument is supplied, so the recipe passes the Conan include path explicitly
and injects the Conan library directory into `LDFLAGS`; the macro then finds
`-lsqlite3` through its normal search path.

The three OHOS patches add target-triplet recognition and make configure's
private temporary directory compatible with HMDFS permissions. Two additional
patches keep the vendored Cgreen/test sources buildable with modern clang; the
second fixes an upstream test-only type error in the legacy mSQL branch.

## Test coverage

The release tarball contains 13 upstream test entry points under `tests/`: 11
`test_*.sh` scripts and the `test_dbi`/`test_dbi_dlopen` programs they invoke.
The recipe intentionally packages only SQLite3, so the 9 optional-driver
script entries that need legacy SQLite, MySQL, PostgreSQL, DB2, Firebird,
FreeTDS, Ingres, mSQL, or Oracle client/server stacks are not silently counted
as passed. The two upstream programs are built and invoked indirectly by the
selected scripts and are not double-counted.

The two available SQLite3-related entries were exercised: the deterministic
dynamic-loader check with `make check TESTS=test_libdbi.sh` passed, while
`tests/test_sqlite3.sh` was executed and failed in the old libdbi matrix's
plain-`char` and unsupported numeric-conversion assumptions before raising a
signal. Thus the release-entry pass rate is 1/13; the 9 optional-driver script
entries are explicitly NOT RUN because their database-specific dependencies
are outside the reproducible SQLite3-only closure. The Conan consumer
separately initializes libdbi with the packaged `libdbdsqlite3.so`, creates a
database, inserts a row, and reads it back using public libdbi APIs (15/15
assertions).

## Verification results

- `conan create ... -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`: passed on the OHOS AArch64 worker.
- Upstream inventory: 13 release test entry points (11 scripts + `test_dbi`/`test_dbi_dlopen`).
- Upstream executed result: 1/13 passed; `test_libdbi.sh` passed and `test_sqlite3.sh` failed with the documented OHOS limitation; 9 optional-driver script entries are explicitly NOT RUN because their client/server stacks are not in scope, while the two programs are rolled into the invoking scripts.
- Conan `test_package`: passed; the consumer reported `15 libdbi-drivers assertions`.
- Packaged artifact: `lib/dbd/libdbdsqlite3.so`.
- Full `tests/test_sqlite3.sh`: retained as a known OHOS test-harness limitation; its failure is recorded rather than hidden.

## Clean verification

A fresh source extraction with all five patches applied passed configure, make,
and make install when the OHOS shell and the actual Conan dependency package
paths were supplied to the clean verifier. The stock helper does not resolve
Conan dependency paths on its own; that dependency discovery limitation is
recorded in `reports/test-report.md`.

## Finish record

### 对话 #1 — 2026-09-21

- Regenerated the config.guess/config.sub patches against the exact clean source;
  all five patches apply successfully.
- Confirmed the normal Conan route with the SQLite3-only scope, selected loader
  test, public consumer, and transparent full-suite limitation.
- Added software-level metadata and the clean verification/test report.
---

**编译结束**: 2026-09-26 12:29
**最终状态**: built
