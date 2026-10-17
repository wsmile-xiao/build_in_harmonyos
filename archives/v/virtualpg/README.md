# VirtualPG

VirtualPG exposes PostgreSQL tables through SQLite's virtual-table API. It ships a reusable C library and a loadable SQLite extension.

## Versions

| Version | Status | Build system | Required dependencies |
| --- | --- | --- | --- |
| 2.0.1.1 | built | Autotools | sqlite3/3.49.1, libpq/18.1 |

The OpenHarmony recipe uses the upstream source release, adds native `linux-ohos` triplet recognition, keeps Autoconf temporary directories writable on HMDFS, and packages relocatable library and pkg-config metadata. Shared and static packages were built and exercised on HarmonyOS 6.0/AArch64; publication remains CI-controlled.
