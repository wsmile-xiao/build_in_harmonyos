# guile

GNU Guile is a Scheme interpreter and embeddable extension library.

- Upstream: https://www.gnu.org/software/guile/
- License: LGPL-3.0-or-later
- Build system: Autotools
- Package type: library with command-line tools

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 2.2.7 | built | OHOS recipe uses Conan-managed gc, gmp, libffi, libunistring and libtool dependencies. |
| 2.2.7.1 | built | Fixes runtime dependency search paths for downstream tools. |
| 2.2.7.2 | built | Makes consumer command and C API failures fail the package test; fixes a test patch hunk. OHOS `conan-verify` and W3 local CI passed. |
