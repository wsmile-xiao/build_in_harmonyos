# libdb

libdb is Berkeley DB — an embedded transactional key/value storage engine
(B-tree / Hash / Heap / Queue / Recno) with ACID transactions, locking,
write-ahead logging, MVCC snapshot isolation and replication.

This archive entry is the **community fork** [berkeleydb/libdb](https://github.com/berkeleydb/libdb)
(its README opens with *"Not affiliated with or endorsed by Oracle"*; Oracle's
last 5.3 release was 5.3.28, and v5.3.29 and later are community releases).
It is a distinct software entry from `berkeley-db5/5.3.28` (sourced from
download.oracle.com) and `db/6.2.32` (the Oracle 6.x AGPL line): different
source origin, homepage, version line, license wording and build system.

This entry adapts libdb 5.3.35 for OpenHarmony PC through a Conan/Meson package.
The fork added a Meson build alongside the legacy Autotools path; this recipe
uses Meson, which generates neither `config.status` nor libtool and therefore
avoids the three HMDFS environmental pitfalls that the Autotools BDB recipes
have to patch around (the `print -r --` echo-probe false positive, the
`(umask 077 && mktemp -d)` refusal on setgid directories, and the 2011-era
`config.guess` / `config.sub` not knowing the HarmonyOS triplet).

The upstream Meson test suite is executed in `upstream_test_in_build`
(the gating `tiers` suite, 1/1), and the packaged artifact is exercised by a
consumer test covering version identity, the B-tree engine, multi-threaded
concurrent writes, on-disk persistence and a deterministic error path.
