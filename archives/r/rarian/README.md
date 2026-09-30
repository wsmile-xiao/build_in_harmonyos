# rarian

Rarian is a documentation metadata library based on the Freedesktop spec; it replaces Scrollkeeper and ships scrollkeeper-compatible commands.

## OHOS adaptation

- Autotools native build on HarmonyOS aarch64 with clang.
- The only linked dependency is `tinyxml2` (`RARIAN_LIBS=-ltinyxml2`); `xsltproc` is an optional runtime helper for one compat script and degrades gracefully when absent.
- Install passes `--disable-skdb-update` so packaging never touches the host help database.
- Upstream `make check` builds `tests/check_rarian` (libcheck, 8 suites / 29 cases); case counts are parsed from `tests/check_rarian.log`.
- Public headers require `#define I_KNOW_RARIAN_0_8_IS_UNSTABLE` before `#include <rarian.h>`; the consumer test follows this.

## Dependencies

- `tinyxml2/11.0.0` (link dependency)
- `check/0.15.2` (test_requires, upstream suite only)
- `pkgconf/3.0.5` (tool_requires, `PKG_CHECK_MODULES` for check)

## References

- https://rarian.freedesktop.org/
- https://gitlab.freedesktop.org/rarian/rarian
