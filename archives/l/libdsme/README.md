# libdsme

libdsme is the DSME (Device State Management Entity) socket IPC library plus
the DSME and Thermal Manager D-Bus interface definition modules from the
Sailfish OS project. It provides the `dsmesock_*` client protocol
(connect/send/receive/broadcast with peer credentials), the `dsmemsg_*`
message helpers, alarm-limit constants and the shared D-Bus name tables used
by DSME clients.

Upstream: https://github.com/sailfishos/libdsme

## OHOS adaptation

- Builds the official release tarball with the upstream hand-written
  Makefile; no build-system replacement.
- Adds abstract AF_UNIX socket support to `dsmesock_connect()`
  (`@name` prefix). OHOS cannot create file system unix sockets (HMDFS
  `bind()` returns EPERM and `/tmp` is read-only), so abstract names are the
  only usable AF_UNIX transport in OHOS sandboxes.
- Runs the complete upstream Check suite (`tests/ut_libdsme`, 2/2 cases) from
  the recipe; the upstream Makefile only builds it.
- Ships relocatable pkg-config metadata and the upstream SONAME layout
  (`libdsme.so.0`, `libdsme_dbus_if.so.0`, `libthermalmanager_dbus_if.so.0`).

## Dependencies

- `glib/2.84.0.1` — GLib `GSList` used by the dsmesock connection bookkeeping.
- `check/0.15.2` — test-only dependency of the upstream unit test suite.

## References

- https://github.com/sailfishos/libdsme
- https://github.com/sailfishos/libdsme/releases/tag/0.67.0
