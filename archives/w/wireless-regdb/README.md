# wireless-regdb

The Linux wireless regulatory database contains per-country frequency,
bandwidth, power, DFS, and WMM rules used by the wireless regulatory stack.

The package installs the authoritative text database, compiled database, and
signature under:

`share/wireless-regdb`

With Conan build or run environments enabled, `WIRELESS_REGDB` points to the
compiled `regulatory.db` and `WIRELESS_REGDB_DIR` points to its directory.

The architecture-independent package also retains the upstream `dbparse.py`
and `db2fw.py` tools under `share/wireless-regdb/tools` so consumers can parse
or reproduce the compiled database without network access.
