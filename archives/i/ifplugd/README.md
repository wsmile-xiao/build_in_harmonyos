# ifplugd

ifplugd is a Linux daemon which automatically configures an Ethernet interface when a cable is plugged in and unconfigures it when the cable is pulled. Useful on laptops with onboard network adapters.

## Features
- Link detection via MII, ethtool, wireless extensions, IFF_RUNNING and netlink monitor
- Multiple interface support (`-i` per instance)
- Configurable up/down delays (`-u`/`-d`), poll time (`-t`), API mode (`-m`)
- Syslog support, beep notification, suspend/resume (`-S`/`-R`)
- Ships two binaries: `ifplugd` (daemon) and `ifplugstatus` (link query)

## OHOS adaptation
- Build system: autotools (`configure` + `make -j1`; HMDFS denies mkfifo so jobserver needs `-j1`)
- Dependency: `libdaemon/0.14` via `PkgConfigDeps` (upstream `PKG_CHECK_MODULES(LIBDAEMON, libdaemon >= 0.5)`)
- Configure flags: `--disable-lynx --disable-xmltoman --disable-subversion` (doc-only tools, hard-abort without them), `--with-initdir=<prefix>/etc/init.d` (upstream requires initdir, OHOS has no /etc/init.d), explicit `--build/--host` triplets for the 2005-era config.sub, `ac_cv_func_malloc/realloc` cache seeds (AC_FUNC_MALLOC cross false positive)
- `configure` scratch-dir `umask 077` relaxed to `022` at build time (HMDFS setgid, same as ifmetric/iec16022 precedent) via `replace_in_file`, keeping real mktemp/mkdir
- Upstream ships zero automated tests (no TESTS/check_PROGRAMS/tests dir); consumer test drives the real binaries' option parsers without touching interfaces or routes (no root needed)

## Dependencies
- Build: libdaemon/0.14
- Runtime: libc only

## References
- Upstream: https://0pointer.de/lennart/projects/ifplugd/
- Source: https://0pointer.de/lennart/projects/ifplugd/ifplugd-0.28.tar.gz
