# audtty

ncurses based frontend to audacious. Lightweight terminal UI that controls Audacious via D-Bus.

- **Upstream**: http://audtty.alioth.debian.org (Vcs-Git: git://git.code-monkeys.org/audtty.git)
- **Version**: 0.1.12
- **License**: GPL-2.0-or-later
- **Build system**: Autotools (configure + make)

## OHOS Adaptation

- **Stub audclient**: Audacious (libaudclient) is not in the OHOS registry. The recipe vendors a minimal `libaudclient` stub (headers `audacious/audctrl.h`, `audacious/dbus.h`, pkg-config `audclient.pc`, static lib `libaudclient.a`) that implements all `audacious_remote_*` symbols as no-ops. This satisfies `PKG_CHECK_MODULES(audclient)` and links the binary; `--help`/`--version` work without a running Audacious.
- **Debian patches**: DESTDIR fix, DSO linking (LDADD), glib cflags, audclient pkg name.
- **Modern glib**: Guard `g_type_init()` with `GLIB_CHECK_VERSION(2,36,0)`.
- **HMDFS**: `umask 077` → `022` for tmp dirs in `configure`/`config.status`.

## Dependencies

- `glib/2.88.0`
- `dbus/1.14.10`
- `dbus-glib/0.114`
- `ncurses/6.6` (widechar, static)

## Test

- `audtty --help` and `audtty --version` smoke tests (2 cases).
- Upstream has no test suite (`make check` not defined); declared `upstream_tests_exist: false` with audit.
