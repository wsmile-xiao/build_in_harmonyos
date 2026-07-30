# EB Library 4.4.3 adaptation notes

## Scope

- Upstream is a C library and command-line tool suite, despite the contest row being labeled C++.
- The build system is Autotools and the release archive includes generated configure files.
- The release must be built in source because the utility Makefiles do not provide a correct top-level include path for out-of-source builds.
- The package is built static-only so the installed tools do not require a separately signed libeb shared object.

## Dependencies

- Required: `zlib/1.3.1` for EBZIP compression and bitmap conversion.
- Optional NLS/gettext support is disabled. It is not required for the library API or command functionality.
- iconv remains an optional configure-time capability supplied by the platform C library when available.
- pthread and EBNET/IPv6 support are enabled.

## Patches

- `0001-fix-pthread-lock-and-ebnet-path.patch` fixes `eb_is_text_stopped()` using the address of `EB_Book.lock` and restores the missing unlock. It also moves the EBNET terminator inside its fixed-size path buffer.
- `0002-fix-hmdfs-umask.patch` changes Autoconf temporary-directory creation from `umask 077` to `umask 022`, which allows `config.status` to write temporary files on the HMDFS filesystem used by OpenHarmony devices.

## Tests

Upstream has no registered Automake `TESTS`; `make check` is therefore non-substantive. The recipe builds upstream samples and runs `samples/initexit`, which exercises `eb_initialize_library()` and `eb_finalize_library()` without external dictionary data. The Conan consumer test adds version, pthread, book lifecycle, and error API checks.

## Validation status

- Official source archive SHA256: verified.
- Native Linux configure/build/install, Conan package creation, consumer test, and upstream sample: passed.
- OHOS 6.0 aarch64 true-device build, samples, consumer test, and CI gates: passed.
