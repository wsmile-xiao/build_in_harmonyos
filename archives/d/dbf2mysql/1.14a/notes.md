# dbf2mysql 1.14a OHOS adaptation notes

## Build environment

- Target: OHOS 6.0, armv8
- Compiler: Clang 15
- Build system: raw Makefile
- Dependency: `mariadb-connector-c/3.4.8`
- Status: built (publication is reported separately)

## Source provenance

The upstream SourceForge project is unmaintained and explicitly says its
release files are bogus and CVS should be used. Its official downloadable CVS
snapshot contains the RCS repository rather than a buildable checkout. The
Debian `dbf2mysql_1.14a.orig.tar.gz` pristine upstream tarball is therefore used
under the repository's PF7 official-hosting exception. Its SHA-256 is
`34a1865308d38e52244646ddf9e82d77b56de37361be73ec166c61620bb6e2f6`.

## Adaptation

The legacy sources call `mysql_connect()`, which is absent from current MySQL
C API compatible headers. Patch `0001-use-mysql-real-connect.patch` initializes
the connection handle with `mysql_init()` and connects with
`mysql_real_connect()`. No OHOS-specific fake implementation is introduced.

The recipe builds `dbf2mysql` and `mysql2dbf` with the Conan-selected C compiler,
links them to `libmariadb`, and installs both under `bin/`.

## Tests

The upstream source has no `check` or `test` target and contains no automated
test suite (0 upstream assertions). The consumer package runs 12 assertions:
both executables must be installed and executable; both must report version
`1.14a` and usage with the documented nonzero status; and both DBF input/output
error paths must produce the expected diagnostics. No live MySQL/MariaDB server
was available, so database transfer is not claimed as tested.
