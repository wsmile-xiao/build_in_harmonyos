# libzeitgeist 1.0.4

## Source and build

Zeitgeist 1.0.4 is an Autotools project whose core library and daemon are
written in Vala. The release tarball contains Vala sources, but generates C,
headers, VAPI files, and the library during the build, so `vala/0.56.18` is a
build tool requirement.

The core configure check requires GLib 2.35.4 and SQLite 3.7.11. Datahub is
enabled by default upstream and would add GTK, JSON-GLib, and optionally
Telepathy; this recipe disables Datahub and its providers because the
`libzeitgeist-2.0` API does not require them. FTS is also disabled, so Xapian
is not a dependency of this package.

## OpenHarmony changes

- `build-aux/config.guess` recognizes HarmonyOS and returns
  `aarch64-unknown-linux-ohos`.
- `build-aux/config.sub` accepts `linux-ohos` in the target triplet.
- `configure` uses umask 022 for temporary files on HMDFS.
- A generator-local `sqlite3.pc` is created because the existing SQLite
  package exports headers and `libsqlite3.a` but no pkg-config file.

## Verification boundary

The test package calls the public Event/Subject API. The upstream tests are
available through `make check`, but their D-Bus tests need a runnable D-Bus
session/service and must be reported separately from a library consumer smoke
test. This Windows environment has no Conan or OHOS target toolchain, so no
target build result is claimed here.

## Upstream direct suite on a HarmonyOS PC (2026-09-02)

The upstream `test/direct` suite was executed on-device in the `conan create`
build tree (upstream `make check` with an `AM_VALAFLAGS` override that only
injects vapi paths and `top_builddir`; no test content changes):

```
PASS: datamodel-test datasource-test event-test marshalling-test mimetype-test
PASS: monitor-test query-operators-test symbol-test table-lookup-test where-clause-test
# PASS: 10  # FAIL: 1  # ERROR: 0
```

`log-test` fails in setup because its cases spawn a D-Bus session bus:
`Cannot spawn a message bus without a machine-id` — the device has no
`/etc/machine-id` (system paths are not writable) and no dbus-daemon, the
same environment boundary as the `test/dbus` integration scripts.  Upstream
CI executes those with a D-Bus-capable Linux environment.
