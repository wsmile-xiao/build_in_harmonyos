# percona-server 8.4.10_10 test report

## Scope

- Package: `percona-server/8.4.10_10`
- Target: HarmonyOS PC AArch64
- Package surface: client library and client tools, with server/router disabled
- Status: build/package/consumer-link/target-execution validated on a remote HarmonyOS PC

## Upstream Test Inventory

The pinned upstream source **does contain** the MySQL Test (MTR) suite:

| Source inventory | Count | Evidence |
| --- | ---: | --- |
| `mysql-test/*.test` and suite test files | 10,422 | Complete pinned source snapshot |
| `mysql-test/*.result` and suite result files | 10,261 | Complete pinned source snapshot |
| Total files under patched `mysql-test` | 26,985 | Frozen target validation input |
| Source files under `unittest` | 583 | Complete pinned source snapshot |

## Unit Test Validation

The final patched full-server target `merge_large_tests-t` was rebuilt on the
HarmonyOS PC target after patch 0047. Its 1,979 listed tests ran in 16
exact-source shards with all 16 shard exit codes 0. The isolated
`Bgc_ticket_manager_test.Several_tickets_test` also passed independently in
26.6 seconds after the OHOS busy-wait portability fix.

The BGC test keeps the upstream 300-thread by 100-loop workload. Patch 0047
makes the random engine/distribution thread-local and replaces the two OHOS
busy-wait `yield()` loops with 1 microsecond sleeps; non-OHOS behavior remains
unchanged. No test cases were removed and no loop counts were reduced.

The full-server target also rebuilt `merge_innodb_tests-t` after patch 0048.
The generated exact-source manifest parsed 952 test entries into 16 sequential
shards. All 16 shard processes exited 0; each shard retained two upstream
disabled entries, so 920 tests executed and passed. Patch 0048 skips only the
optional Linux procfs-dependent NDB hardware-statistics initialization on OHOS;
it does not synthesize procfs data or remove NDB test assertions.

## Full-server CTest

The final full-server CTest run listed and executed 142 tests. All 142 passed
with 0 failures in 707.21 seconds. `merge_large_tests`,
`merge_innodb_tests-t`, and `merge_small_tests` passed in the same run.

Patch 0055 makes InnoDB thread-priority changes a no-op on OHOS. The target
libc rejects the Linux `setpriority()` path selected by the upstream Linux
configuration, and the resulting warning was treated as an MTR error.

## MTR validation

The upstream-required `main.1st` test passed after patch 0055: 2/2 MTR
entries passed, including startup and shutdown. The complete MTR suite is
running separately with `--nounit-tests`, `--parallel=2`, and writable target
temporary directories; its final pass/fail result is pending and must not be
represented as complete until the exit status is captured.

`mysql-test/README` documents `mysql-test-run.pl`/`mtr`, and upstream
`CONTRIBUTING.md` requires at least the `main.1st` start-and-shutdown test for a
full server build. The Conan package remains intentionally client-only:
`WITHOUT_SERVER=ON` prevents its build graph from adding `mysql-test`, and
`WITH_UNIT_TESTS=OFF` prevents its unit-test directories from being added. A
separate full-server target build is used for MTR and CTest validation; those
results do not change the delivered Conan package surface.

## Checks

| Stage | Result | Evidence |
| --- | --- | --- |
| W0 dependency recipe gate | PASS | Fresh Conan home could download `openssl/3.5.6.1.1` and `ncurses/6.6` recipes from `ohpcd`. |
| Python syntax | PASS | `python -m py_compile conanfile.py test_package/conanfile.py` completed successfully. |
| Patch applicability | PASS | The zero-context OHOS patch passes `git apply --check --unidiff-zero` against a clean upstream source tree, and remote `conan source .` replayed it successfully. |
| Conan create | PASS | Remote HarmonyOS PC `conan create` exited with code 0; log SHA256 `e026c23df450cb6528df956d55bb109b88a602f7acc170b791d955bca126919f`. |
| Package artifacts | PASS | Package contains `libperconaserverclient.a`, public headers, `mysql`, and `mysql_config`. |
| Consumer build | PASS | `test_package` built the C target `test_percona_server_client`. |
| Target execution | PASS | `test_package` executed on the target and printed `percona-client:8.4.10-10:80410:1`. |
| Full-server CTest | PASS | 142/142 tests passed; 0 failures; 707.21 seconds. |
| BGC unit test | PASS | `Bgc_ticket_manager_test.Several_tickets_test`: 1/1 passed in 26.6 seconds. |
| Upstream `main.1st` | PASS | 2/2 MTR entries passed after the OHOS InnoDB priority no-op fix. |
| Full-server InnoDB unit tests | PASS | `merge_innodb_tests-t`: 16/16 exact-source shards exited 0; 920 executed tests passed and 32 upstream-disabled entries were retained. |

## Result Summary

| Metric | Count |
| --- | ---: |
| Total validation checks | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 1 (complete MTR) |

## Boundaries

- This report proves the local/remote adaptation evidence listed above.
- Complete MTR remains pending; this report does not claim the full MTR suite
  passed until its final log and exit status are archived.
- Current package reference: `percona-server/8.4.10_10#0367aef34d81dbe7fc9bb0d58363ea2d:b32e95946afda220db8287f449b037f206c3d8ff#d8c734ff432db966e415c7cbc960b39b`.
- This report does not prove W4 independent audit, PR CI, merge, or publication.
- Endpoint names, usernames, ports, and remote user paths are intentionally omitted from this public archive report.
- Raw InnoDB shard logs and filters are archived separately at the local
  evidence path configured for this task; the archive SHA256 is
  `92be1cfba9acfb6227872b545473e96ffef875e97d566ac1bda359666d4e0b55`.
