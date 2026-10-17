# rsbackup 10.0 for HarmonyOS PC

This archive packages the upstream C++ backup utility for native OHOS/aarch64.
The recipe uses published `boost/1.90.0.4.4`, `sqlite3/3.53.4`,
`rsync/3.3.0`, and `automake/1.19` packages.

The published OHOS rsync has no ACL support. HMDFS also refuses reads of its
`security.hmmac` xattr during backup. The recipe configures rsbackup without
these two default rsync options, while keeping the upstream defaults available
through configure switches on systems that support them. The optional graph
program is built only when Cairomm and Pangomm are available.

Build natively on HarmonyOS PC with the repository's OHOS/aarch64 Conan
profile. `conan create` runs the full upstream `make check` suite and a
consumer test that performs a real backup with the published rsync binary.

See [notes.md](10.0/notes.md) for test results and limitations.
