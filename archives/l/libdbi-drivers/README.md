# libdbi-drivers

libdbi-drivers provides loadable database drivers for the libdbi C database-abstraction layer. This archive adapts the upstream driver collection for OpenHarmony PC AArch64.

## Package contents

- SQLite3 loadable driver: `lib/dbd/libdbdsqlite3.so`
- Conan dependencies: `libdbi/0.9.0-r5` and `sqlite3/3.53.4`
- No command-line executable

The upstream release also contains drivers for MySQL, PostgreSQL, DB2, Firebird, FreeTDS, Ingres, mSQL, and Oracle. Those drivers require client libraries that are not reproducibly available in this adaptation and are not claimed as supported.

## OpenHarmony adaptation

- Add AArch64 OHOS recognition to the bundled GNU config scripts.
- Make the generated configure temporary-directory setup compatible with HMDFS.
- Pass Conan dependency include/library paths through the legacy Autotools checks.
- Apply narrow modern-clang fixes to the bundled Cgreen and legacy test sources.
- Preserve the driver-module layout under `lib/dbd` and remove Libtool archive files from the package.

The release contains 13 upstream test entry points (11 scripts plus `test_dbi` and `test_dbi_dlopen`). The dynamic-loader entry passes; the SQLite3 matrix was executed and fails on the documented OHOS conversion limitation, while the other 9 optional-driver script entries are explicitly not run because their database-specific client/server stacks are outside this SQLite3-only package. The two programs are rolled into their invoking scripts without double counting. The upstream release-entry rate is therefore 1/13. An independent Conan consumer CRUD test passes 15/15 assertions.

## References

- Homepage: https://libdbi-drivers.sourceforge.net/
- Source: https://sourceforge.net/projects/libdbi-drivers/
- License: LGPL-2.1-or-later
