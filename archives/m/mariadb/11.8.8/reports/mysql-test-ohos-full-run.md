# MariaDB 11.8.8 mysql-test OHOS full runnable-boundary run

## Environment

- Date: 2026-09-05
- Device: OHOS aarch64 real device (`10.62.220.52:2222`)
- Source and build: MariaDB 11.8.8 Conan build `maria7c8e3318eb776`
- Test driver: upstream `mysql-test/mariadb-test-run.pl`
- Execution mode: `--parallel=1`, one private `mariadbd`, no concurrent build
  or test process
- Memory during the full runs stayed around 760-850 MB available with no swap.
  The final 56-case CI-subset rerun started with 13705216 kB available and
  finished with 13961216 kB available.

OHOS HMDFS rejects MariaDB's file-backed Unix socket, so the recipe's test
harness configuration uses loopback TCP when `MTR_TCP_ONLY=1`:

- client and server endpoints use `127.0.0.1`;
- server and client Unix socket paths are empty;
- generated client arguments request `--protocol=tcp`;
- client TLS is skipped only for the default non-TLS harness connections;
- tests that explicitly require TLS still run with their own SSL options;
- `symbolic-links=0` is generated because HMDFS rejects the symlinks used by
  some server data-directory operations;
- InnoDB treats every non-`EINTR` `posix_fallocate()` rejection as nonfatal and
  falls back to the portable zero-writing path; OHOS was observed returning
  `EACCES` (error 13).

These are harness/build adaptations; no upstream `.test` file is modified.

## Commands

The complete `main` suite was invoked first:

```bash
cd "$SOURCE/mysql-test"
MTR_BINDIR="$BUILD/Release" \
MTR_TCP_ONLY=1 \
MTR_BUILD_THREAD=350 \
TMPDIR="$BASE/tmp-main-full-tcp" \
perl ./mariadb-test-run.pl \
  --force --max-test-fail=0 --parallel=1 --timer --suite=main \
  --testcase-timeout=3 --suite-timeout=240 \
  --vardir="$BASE/var-main-full-tcp" \
  --tmpdir="$BASE/tmp-main-full-tcp"
```

The complete `binlog` and `client` suites were then invoked in a fresh vardir:

```bash
cd "$SOURCE/mysql-test"
MTR_BINDIR="$BUILD/Release" \
MTR_TCP_ONLY=1 \
MTR_BUILD_THREAD=350 \
TMPDIR="$BASE/tmp-binlog-client-full-tcp" \
perl ./mariadb-test-run.pl \
  --force --max-test-fail=0 --parallel=1 --timer \
  --suite=binlog,client --testcase-timeout=10 --suite-timeout=360 \
  --vardir="$BASE/var-binlog-client-full-tcp" \
  --tmpdir="$BASE/tmp-binlog-client-full-tcp"
```

After the InnoDB and modern-runner socket fixes, targeted reruns covered the
affected main cases. The final table below merges the full runs and those
targeted retries by MTR combination: the newest status for a combination wins,
and a unique test is counted as failed if any of its combinations remains
failed. Skipped and disabled tests are never counted as passed.

## Results

| Scope | Independent tests | Passed | Failed | Skipped | Disabled |
|---|---:|---:|---:|---:|---:|
| `main` | 1356 | 1012 | 59 | 279 | 6 |
| `binlog` + `client` | 161 | 112 | 11 | 38 | 0 |
| **Combined** | **1517** | **1124** | **70** | **317** | **6** |

MTR expands some tests into format combinations. At combination granularity the
result is 1210 passed, 83 failed, 357 skipped, and 6 disabled out of 1656.

The strict upstream pass rate is therefore **1124/6650 (16.90%)**. Among the
1194 independent tests that were neither skipped nor disabled, 1124 passed
(94.14%). The lower number is the PR-reported result because skipped and
disabled tests do not count as passes.

The CI gate does not rerun all 1517 tests on every package build. It fixes a
serial subset of 56 real-device-verified passing `main` cases. After the final
harness changes, that subset was rerun in a fresh vardir:

```text
Completed: All 56 tests were successful.
Spent 110.385 of 289 seconds executing testcases
MTR exit code: 0
```

CI #40518 subsequently exposed a recipe bug: the earlier `EACCES/EPERM` matcher
omitted the indentation present in the official source, so a fresh CI source
tree did not receive the fix that had been verified manually on the real device.
The recipe now matches the official indentation and changes the failure branch
to the generic portable fallback. After recompiling `os0file.cc`, rebuilding
`libinnobase.a` and `mariadbd`, the five CI failures (`main.costs`,
`main.analyze`, `main.delete`, `main.alter_table_autoinc-5574`, and
`main.default`) passed 5/5, and the complete 56-case CI subset again reported:

```text
Completed: All 56 tests were successful.
Spent 83.434 of 263 seconds executing testcases
MTR exit code: 0
```

## 6650-file mapping

`mysql-test/**/*.test` contains 6650 files in the official source archive
(re-verified 2026-09-07 by unpacking
`mariadb-11.8.8.tar.gz` (SHA-256 `bd023a49…c524c9`, identical to
`conandata.yml`) and running `find mysql-test -name '*.test' | wc -l` → 6650;
no git clone is needed). The executed boundary covers the complete `main` suite
plus the complete `binlog` and `client` suites:

| Boundary | `.test` files | Independent MTR tests |
|---|---:|---:|
| `main` | 1356 | 1356 |
| `suite/binlog` | 172 | 156 |
| `suite/client` | 5 | 5 |
| **Executed** | **1533** | **1517** |

The 16 `.test` files under `suite/binlog/include/` are shared includes rather
than independently discovered MTR tests. File coverage is 1533/6650 (23.05%).

The remaining 5117 files were re-classified at suite granularity on 2026-09-07.
Every suite falls into exactly one of two classes; 2204 + 2913 = 5117.

### Class B — blocked by build configuration, topology, or environment (2913)

| Suites | `.test` files | Specific blocking reason |
|---|---:|---|
| `rpl` (715), `multi_source` (22) | 737 | each case starts a 2–4 `mariadbd` replication topology with GTID sync; the validation budget is a single real device, serial `--parallel=1`, one vardir, suite timeouts — a 715-file multi-server serial farm is not executable within it (environment limitation) |
| `galera` (492), `galera_sr` (102), `galera_3nodes` (43), `galera_3nodes_sr` (17), `wsrep` (31) | 685 | wsrep cluster provider is not compiled (build does not enable `WITH_WSREP`); cluster coordination unavailable (OHOS missing feature in this build) |
| `perfschema` (459), `perfschema_stress` (4), `sysschema` (93) | 556 | `PLUGIN_PERFSCHEMA=NO` in the recipe — server has no performance_schema / sys-schema objects to observe (build configuration) |
| `mariabackup` (100) | 100 | `WITH_MARIABACKUP=False` — the `mariadb-backup` binary is not built (build configuration) |
| `s3` (22) | 22 | `PLUGIN_S3=NO` — S3 engine and its external S3 endpoint are absent (build configuration + external service) |
| `encryption` (73), `binlog_encryption` (65) | 138 | require dynamic `file_key_management`/encryption-provider plugin `.so` files and key/certificate rotation services; the `minbuild` target (top-level `CMakeLists.txt`, `ADD_CUSTOM_TARGET(minbuild)`) builds only the static server and client tool set, no dynamic plugins (build product boundary) |
| `engines` (427), `storage_engine` (121) | 548 | engine-matrix suites that run against dedicated/external engine server binaries and `--extern` matrices not produced by this build (build product boundary) |
| `plugins` (43), `federated` (27), `archive` (16) | 86 | depend on dynamic plugin `.so` targets (`ha_federatedx`, `ha_archive`, daemon/fulltext plugins) not in the `minbuild` product; several upstream plugins are additionally disabled via `PLUGIN_ROCKSDB/SPIDER/MROONGA/…=NO` (build product boundary + build configuration) |
| `stress` (8) | 8 | upstream long-duration concurrent stress design; incompatible with the single-device serial validation budget |
| `optimizer_unfixed_bugs` (22) | 22 | upstream collection of known-unfixed defects with expected-failure semantics; there is no pass meaning to claim |
| `mtr` (7), `mtr2` (1) | 8 | mysql-test-run framework self-tests, not server features |
| `include` | 3 | shared include files, not independent tests |
| **Total blocked** | **2913** | |

### Class A — runnable but not executed (2204)

Single-server suites whose engines (InnoDB, Aria, MyISAM, MEMORY, CSV, SEQUENCE)
are statically compiled into the produced `mariadbd`. No platform or build
blocker exists for them; they exceeded the serial single-device budget of the
2026-09-05 runs and are **not** claimed as passed. They are the incremental
follow-up scope once a validation device is available again.

| Suites | `.test` files |
|---|---:|
| `sys_vars` | 755 |
| `innodb` (447), `innodb_fts` (50), `innodb_gis` (42), `innodb_i_s` (29), `innodb_zip` (24) | 592 |
| `parts` | 142 |
| `funcs_1` (123), `funcs_2` (4) | 127 |
| `jp` | 111 |
| `compat` | 90 |
| `maria` | 66 |
| `vcol` (59), `roles` (57), `gcol` (49), `versioning` (33), `sql_sequence` (28), `atomic` (26) | 252 |
| `events` (15), `json` (12), `period` (10), `heap` (8), `handler` (8), `csv` (7), `merge` (5), `large_tests` (4) | 69 |
| **Total runnable-unexecuted** | **2204** |

This mapping explains why the 1124-pass numerator is reported against all 6650
upstream files. It does not treat unexecuted suites as successful.

## Failure triage

The 70 failed independent tests fall into six reproducible domains. Root
causes are tied to the concrete build configuration; the two fixable domains
found during the 2026-09-05 runs (Unix-socket prohibition and InnoDB
`posix_fallocate()` EACCES) were fixed before attribution — see the harness
notes at the top of this report:

| Domain | Failed tests | Root cause and representative error |
|---|---:|---|
| Client tooling / TLS / secure transport | 30 | build uses bundled wolfSSL with `CONC_WITH_SSL=OPENSSL` bridging (chosen to avoid external OpenSSL deps on OHOS); the compatibility layer diverges on handshake/certificate/protocol assertions — representative log `TLS/SSL error: error state on socket`; SSL certificate and protocol tests |
| Authentication, privileges, system catalog | 14 | `PLUGIN_AUTH_ED25519=NO` and other auth/password-validation plugins not built (minbuild has no dynamic plugins); account lock / password expiration / access-denial fixture semantics |
| Filesystem, symlink, and file permissions | 6 | OHOS HMDFS rejects symlinks and differs on chmod-dependent result expectations (environment limitation) |
| Server lifecycle, crash, or TCP harness boundary | 4 | `main.mdev-33070` server SIGSEGV — an upstream defect: rerun by itself reproduces signal 11; shutdown/socket-conflict handling |
| SQL/result expectations | 5 | charset, trigger, BLOB, timestamp, and flush-log result differences |
| `binlog`/`client` suite | 11 | mysqlbinlog filtering/warning assertions, mixed-format differences, client environment behavior |

None of these failures is counted as passed. `main.mdev-33070` was also rerun
by itself and reproduced the server signal-11 failure, so it is not a transient
full-suite artifact.

The 317 skipped independent tests are MTR's own prerequisite skips (missing
plugin binaries such as perfschema/ed25519, TLS prerequisites, debug-only
features, platform feature probes); skips are never counted as passes. The 6
disabled tests are disabled upstream in `disabled.def`.

## Evidence

Raw logs and per-test artifacts are retained on the validation device under
`/storage/Users/currentUser/tmp/mariadb-mtr-tcp/`:

```text
main-full-tcp.log
main-missing9-tcp.log
main-failed-retry-tcp.log
main-failed-retry-r2-tcp.log
main-mdev-33070-tcp.log
binlog-client-full-tcp.log
ci56-fresh-20260905.log
var-main-full-tcp/log/
var-binlog-client-full-tcp/log/
var-ci56-fresh-20260905/log/
```

The initial single-invocation summaries were `Failed 122/1078 tests` for
`main` and `Failed 21/208 tests` for `binlog`/`client`; targeted retries then
replaced affected combination statuses as described above. The combined table
uses the conservative final merged statuses.
