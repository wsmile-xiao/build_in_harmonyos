# libghthash 0.6.2

Generic hash table library for C (Simon Kagstrom, LGPL-2.0-or-later).

## Upstream

- Source: https://github.com/SimonKagstrom/libghthash/archive/refs/tags/v0.6.2.tar.gz
- sha256: e7e5f77df3e2a9152e0805f279ac048af9e572b83e60d29257cc754f8f9c22d6
- Public header: `ght_hash_table.h` (generated from `src/ght_hash_table.h.in`)
- Sources: `src/hash_table.c`, `src/hash_functions.c`
- No external dependencies (only standard C headers)

## Build approach

The upstream tarball ships an old-style autotools setup (`configure.in`
with deprecated `AM_INIT_AUTOMAKE`/`AM_PROG_LIBTOOL`). The build host's
automake 1.17 has a broken Perl module (`Automake::Config.pm` missing),
so `autoreconf` cannot run. The recipe therefore compiles the two C
source files directly with the OHOS clang toolchain, generating the
public header by substituting `@INT32_T@` → `int` in
`ght_hash_table.h.in` (`int` is 4 bytes on aarch64, matching what
configure's size detection would pick).

No patches are applied. The library is built as a static archive
(`libghthash.a`) to avoid shared-library signing complexity in the test
package.

## HarmonyOS validation

`conan create` and the consumer test pass on OHOS armv8. The test
exercises `ght_create`, `ght_insert`, `ght_get`, `ght_remove`,
`ght_size`, and `ght_finalize` — creating a table, inserting a key,
retrieving and verifying the value, removing the key, and confirming
the table is empty.
