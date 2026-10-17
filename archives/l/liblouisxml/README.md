# liblouisxml

liblouisxml is an open-source braille transcription library providing XML, HTML and text to braille conversion via liblouis.

## OHOS adaptation

- Builds the official 2.4.0 release with its generated Autotools files.
- Bundles liblouis 3.33.0 as a private static dependency to satisfy `PKG_CHECK_MODULES([liblouis])` without requiring an external Conan package.
- Uses `AutotoolsDeps`/`PkgConfigDeps` for libxml2 and the private liblouis prefix via `PKG_CONFIG_PATH`.
- Disables the Python bindings (removes `python` from `SUBDIRS`) to avoid a hard Python.h dependency on OHOS.
- Runs the upstream `make check` target (`tests/check_version`) as the build-time upstream test.
- Runs installed-package consumers for `lbx_version()` and `lbx_translateString()`.

## Dependencies

- `libxml2/2.15.3` supplies `libxml-2.0` (via pkg-config).

liblouis 3.33.0 is built privately from source during the package build and linked statically; no external `liblouis` Conan requirement is needed.

## References

- https://github.com/liblouis/liblouisxml
- https://mirror.jmu.edu/pub/ubuntu/pool/universe/libl/liblouisxml/
- https://github.com/liblouis/liblouis
