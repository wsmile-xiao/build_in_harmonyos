# percona-server

Percona Server for MySQL is an open source MySQL-compatible database server.

This archive currently adapts the 8.4.10-10 upstream tag as `percona-server/8.4.10_10`
for the OpenHarmony PC AArch64 environment. The first-stage package scope is the
client-side library and client tools built with `WITHOUT_SERVER=ON`; full `mysqld`
runtime validation is intentionally outside the current package status.

The canonical hyphen form `percona-server/8.4.10-10` (Conan 2 legal version slug,
platform task branch `feat/percona-server-8.4.10-10`) re-verifies the same upstream
tag on-device with an identical recipe and patch set; see `8.4.10-10/notes.md`.
