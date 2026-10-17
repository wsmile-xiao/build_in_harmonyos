# MariaDB 11.8.8 mysql-test OHOS real-device subset

> Historical exploration report (2026-09-04). It is superseded by the complete
> `main` plus `binlog`/`client` boundary run in
> `reports/mysql-test-ohos-full-run.md`; retain it for the initial failure
> triage and CI-subset derivation history.

## Environment

- Date: 2026-09-04
- Device: OHOS aarch64 real device (`10.62.220.52:2222`)
- Server and test driver: MariaDB `minbuild` artifacts from Conan build
  `maria7c8e3318eb776`
- Execution mode: one MTR worker (`--parallel=1`), one `mariadbd`, fixed
  `MTR_BUILD_THREAD=350`, no swap-heavy concurrent jobs
- Memory observed before the runs: about 768-786 MB free with no swap; the
  serial runs stayed in that range

The OHOS HMDFS filesystem rejects creating the file-backed Unix domain socket
used by MariaDB's default mysql-test configuration. The recipe therefore makes
the harness TCP-only when `MTR_TCP_ONLY=1`:

- generated clients use `host=127.0.0.1`;
- generated server/client `socket` values are empty, so `mariadbd` does not
  create a Unix socket;
- MTR's probe-based Unix-socket path checks are skipped for this mode.

## Commands

The source-tree harness was invoked with the existing build tree:

```bash
cd "$SOURCE/mysql-test"
MTR_BINDIR="$BUILD/Release" \
MTR_TCP_ONLY=1 \
MTR_BUILD_THREAD=350 \
TMPDIR="$BASE/tmp" \
perl ./mariadb-test-run.pl \
  --force --max-test-fail=0 --parallel=1 --timer --suite=main \
  --vardir="$BASE/var" --tmpdir="$BASE/tmp" <tests...>
```

The first exploratory batch requested 30 alphabetical `main` tests. MTR
skipped two tests before execution and stopped after reaching the default
limit of 10 failures. The second batch requested 32 tests that do not contain
an explicit `localhost` connection and used `--max-test-fail=0`.

## Results

| Batch | Requested | Executed | Passed | Failed | Skipped |
|---|---:|---:|---:|---:|---:|
| Exploratory main subset | 30 | 26 | 16 | 10 | 2 |
| TCP-compatible main subset | 32 | 32 | 29 | 3 | 0 |
| **Combined unique cases** | **62** | **58** | **45** | **13** | **2** |

The full `mysql-test` baseline contains 6650 `.test` files. Therefore this
real-device validation covered 58/6650 executed cases (0.87%); 45 passed.
The pass rate among executed cases was 45/58 (77.59%). This is a subset result,
not a claim that the remaining 6592 tests passed.

The recipe now runs the 45 cases verified as passing on the real device on
every default full-server Conan build. That CI subset is intentionally kept
separate from the exploratory statistics above; it is not a replacement for the
6650-test baseline.

The exact 45-case recipe subset was then rerun in one fresh MTR invocation and
one vardir:

```text
Completed: All 45 tests were successful.
Spent 116.085 of 231 seconds executing testcases
MTR exit code: 0
```

## Failure Triage

- Explicit `connect ... localhost` statements: `main.aborted_clients`,
  `main.alias`, `main.analyze`, `main.cast`, `main.change_user`,
  `main.check`, `main.create`, and `main.default`. The generated default
  connection is TCP-only, but these test-local commands force `localhost`,
  which mysqltest maps to the disabled Unix socket and fails with
  `Can't connect to local server through socket ''`.
- Missing/disabled InnoDB plugin: `main.costs`, `main.delete`, and
  `main.alter_table_autoinc-5574`. The server log reports that `ib_logfile0`
  is absent and InnoDB plugin initialization aborts; the tests then request
  `ENGINE=InnoDB` and receive `ER_UNKNOWN_STORAGE_ENGINE`.
- Client TLS/tool boundary: `main.binary_to_hex` and `main.compound`. Both
  reach a client tool or helper invocation and fail with
  `TLS/SSL error: error state on socket`; this needs separate client-TLS
  investigation and was not counted as a passed case.
- Skipped tests: `main.cache_temporal_4265` requires a debug server;
  `main.backup_syntax` requires the unavailable `METADATA_LOCK_INFO` plugin.

## Evidence

The complete MTR outputs and per-test artifacts were retained on the validation
device under:

```text
/storage/Users/currentUser/tmp/mariadb-mtr-tcp/main-subset-30-tcp.log
/storage/Users/currentUser/tmp/mariadb-mtr-tcp/main-subset-next-32-tcp.log
/storage/Users/currentUser/tmp/mariadb-mtr-tcp/main-verified-45-tcp.log
/storage/Users/currentUser/tmp/mariadb-mtr-tcp/var-main-subset-30-tcp/log/
/storage/Users/currentUser/tmp/mariadb-mtr-tcp/var-main-subset-next-32-tcp/log/
/storage/Users/currentUser/tmp/mariadb-mtr-tcp/var-main-verified-45-tcp/log/
```

The generated `my.cnf` was inspected during the run and contained
`host=127.0.0.1`, `socket=` in the client section, and an empty server socket.
The server log recorded `Server socket created on IP: '127.0.0.1'` and
`socket: ''`, confirming that the test server actually used TCP rather than a
Unix domain socket.
