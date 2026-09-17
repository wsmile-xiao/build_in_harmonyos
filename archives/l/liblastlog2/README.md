# liblastlog2 — Y2038-safe lastlog library from util-linux

liblastlog2 is the SQLite3-backed, Y2038-safe replacement for the traditional `lastlog` login-tracking library, part of the [util-linux](https://github.com/util-linux/util-linux) suite (since v2.40). It provides the `ll2_*` C API (9 exported symbols) to write, read, rename and remove per-user login records in a SQLite database, and to import legacy fixed-size `lastlog` files.

This Conan package builds **only** `liblastlog2` (shared + static) from the full util-linux source tree, with all util-linux programs and other libraries disabled.

## Main API

`ll2_new_context`, `ll2_unref_context`, `ll2_write_entry`, `ll2_read_entry`, `ll2_read_all`, `ll2_update_login_time`, `ll2_remove_entry`, `ll2_rename_user`, `ll2_import_lastlog`

Header: `<lastlog2.h>` (installed as `include/liblastlog2/lastlog2.h`, matching upstream `lastlog2.pc` `Cflags: -I${includedir}/liblastlog2`).

## Dependencies

- sqlite3 (hard dependency; `sqlite3_open_v2`/`prepare_v2`/`step`/`exec` etc.)
- libc only otherwise: the library does not use PAM, systemd, selinux, utmp/utmpx or other util-linux libraries

## OHOS adaptation

- The build uses `--disable-all-programs --enable-liblastlog2`. `--disable-all-programs` alone also disables liblastlog2 (configure.ac `UL_DEFAULT_ENABLE`), so the explicit enable is mandatory; the configure summary must show `lastlog2 support: yes` because a failed sqlite3 probe silently disables the library.
- `lastlog2.c` includes `<lastlog.h>`, which only glibc provides. The portability patch guards it with `!__GLIBC__` and supplies a layout-compatible `struct lastlog` (only `ll2_import_lastlog()` reads legacy lastlog files; on aarch64 `sizeof(struct lastlog) == 296`, matching glibc). Do not switch the guard to `__OHOS__` — the target clang does not define that macro.
- `config.guess` lacks HarmonyOS detection (patched); `config.sub` v2.42.2 already recognizes `linux-ohos*`.
- The upstream `make check` harness (`tests/run.sh`) shebangs `/bin/bash`, which does not exist on OHOS; the recipe keeps the upstream `make check` invocation and resolves the harness through `bash` via the Makefile's `TESTS_COMMAND` variable.
- HMDFS/umask: autoconf temp dirs (`confXXXXXX`, umask 077) are unwritable on HMDFS; the recipe applies the standard umask 022 + writable `TMPDIR` workaround.

## References

- Upstream: https://github.com/util-linux/util-linux
- Release archive: https://cdn.kernel.org/pub/linux/utils/util-linux/v2.42/
- License: BSD-2-Clause (liblastlog2 subtree `COPYING`, Thorsten Kukuk / SUSE)
