# libdbi-drivers

libdbi-drivers provides database-specific loadable drivers for the libdbi C
abstraction layer. This archive adapts upstream 0.9.0 for OpenHarmony PC
AArch64.

## Package contents

- The upstream SQLite3 driver module `lib/dbd/libdbdsqlite3.so`.
- The libdbi framework and SQLite3 engine remain explicit Conan dependencies.
- No command-line executable is produced.

The legacy upstream release also contains drivers for server and proprietary
databases. The HarmonyOS package deliberately builds the SQLite3 driver because
its headers and static engine are available as reproducible Conan dependencies;
unsupported server-specific drivers are not silently represented as built.

## OpenHarmony adaptation

- Add narrow `config.guess`/`config.sub` recognition for
  `aarch64-unknown-linux-ohos`.
- Use an HMDFS-compatible temporary-directory umask in the generated configure
  script.
- Inject the Conan libdbi and SQLite3 include/library directories into the old
  Autotools checks.
- Keep the loadable module in `lib/dbd` and remove non-relocatable Libtool
  archives.

## Usage

Initialize libdbi with the packaged driver directory, for example:

```c
dbi_initialize_r("<package>/lib/dbd", &instance);
```

Then open the `sqlite3` driver and set `sqlite3_dbdir` and `dbname` before
connecting.

## Validation

- Official SourceForge archive SHA256 is pinned in `conandata.yml`.
- The OHOS recipe runs the deterministic upstream `make check
  TESTS=test_libdbi.sh` loader check; it passes.
- The full legacy `test_sqlite3.sh` matrix remains in the source and was run
  separately, but is not used as the package gate because its assumptions
  about signed plain `char` and unsupported numeric conversions do not hold
  for the OHOS AArch64 `libdbi` dependency.
- The Conan consumer loads the packaged module and executes a SQLite3
  CREATE/INSERT/SELECT sequence through the public libdbi API (15 assertions).
