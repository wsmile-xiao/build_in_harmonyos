# libcom_err

[libcom_err](http://e2fsprogs.sourceforge.net/) is the MIT "common error
description library" (`com_err`) distributed with e2fsprogs. It provides a
compact error-reporting API (`error_message`, `com_err`, `error_table_name`,
`init_error_table`, …) plus the `compile_et` error-table compiler.

This archive builds the `lib/et` subproject of the official **e2fsprogs
1.47.4** release tarball, producing the static `libcom_err` library, the
`com_err.h` header and the `com_err.pc` pkg-config file.

## Versions

| Version | Status |
|---------|--------|
| 1.47.4  | built  |

## Layout

- `libcom_err/` — per-version Conan recipes (`conanfile.py`,
  `conandata.yml`, `manifest.yaml`, `notes.md`, `test_package/`).
