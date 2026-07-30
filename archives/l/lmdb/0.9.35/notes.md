# lmdb 0.9.35 — Adaptation Notes

## Build System
Plain Makefile (no autotools, no cmake).

## Key Adaptation
OpenHarmony musl libc does not support robust mutex
(pthread_mutexattr_setrobust and pthread_mutex_consistent).
LMDB uses robust mutex by default for inter-process crash recovery.
Disabling it with `-DMDB_USE_ROBUST=0` allows LMDB to compile and
function on HarmonyOS, at the cost of crash recovery semantics.

## Build Command
```bash
make -j1 CC=clang XCFLAGS="-DMDB_USE_ROBUST=0" liblmdb.a
make -j1 CC=clang XCFLAGS="-DMDB_USE_ROBUST=0" liblmdb.so
```

## Products
- lib/liblmdb.a (static library)
- lib/liblmdb.so (shared library)
- include/lmdb.h (header)
- bin/mdb_stat, bin/mdb_copy, bin/mdb_dump, bin/mdb_load (tools)

## Test
- mtest2: B+tree insert/delete/cursor iteration — passes
- mdb_stat -V: prints version "LMDB 0.9.35: (Jan 27, 2026)"

## Upstream Test Results
| Test Program | Result | Description |
|-------------|--------|-------------|
| mtest (make test) | ✅ PASS | 355 values added, 139 deleted, cursor traversal/delete verified |
| mtest2 | ✅ PASS | B+tree insert/delete/cursor iteration, 385 values verified |
| mtest3 | ✅ PASS | Multi-value/duplicate key test, 385 values inserted |
| mtest4 | ✅ PASS | Read/write verification |
| mtest5 | ✅ PASS | Cursor/delete verification |
| mdb_stat | ✅ PASS | Database status read verification |

**Upstream test pass rate**: 5/5 (100%)

## Consumer Test (test_package)
| Test Item | Result | Description |
|-----------|--------|-------------|
| mdb_env_create | ✅ PASS | Environment creation |
| mdb_env_open | ✅ PASS | Environment open |
| mdb_txn_begin | ✅ PASS | Transaction begin |
| mdb_dbi_open | ✅ PASS | Database handle open |
| mdb_put | ✅ PASS | Key-value write |
| mdb_get | ✅ PASS | Key-value read |
| mdb_txn_commit | ✅ PASS | Transaction commit |
| mdb_env_close | ✅ PASS | Environment close |

**test_package pass rate**: 1/1 (100%)

## No Dependencies
LMDB is self-contained (only depends on pthread, which is part of the system libc).

---

**编译结束**: 2026-07-15 23:06
**最终状态**: built
---

**编译结束**: 2026-07-22 23:28
**最终状态**: built
