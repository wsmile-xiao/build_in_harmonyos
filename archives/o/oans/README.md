# oans 1.12.0 for HarmonyOS PC

`oans` is a fast duplicate-file scanner and deduplicator. This archive packages the
upstream 1.12.0 command-line tool for OHOS aarch64.

- Upstream: https://github.com/martinus/oans
- License: GPL-2.0-only
- Conan reference: `oans/1.12.0`
- Executables: `oans`, `duperemove`

The recipe uses published `glib/2.84.0`, `sqlite3/3.49.1`, `uuid/2.40.1`, and
`xxhash/0.8.2`, and `gettext/0.22.5`.
The adaptation removes unavailable Linux-only pkg-config probes and handles
HarmonyOS filesystem errors and read-only `/tmp` in the upstream test fixtures.
