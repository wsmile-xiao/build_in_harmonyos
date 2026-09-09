# MariaDB 11.8.8 upstream test scope

## Reproducible count

The official source archive used by this recipe is:

```text
https://archive.mariadb.org/mariadb-11.8.8/source/mariadb-11.8.8.tar.gz
SHA-256: bd023a4959faf012db7f0ebfc0d276729e67e5443df193163f98d80fdfc524c9
```

Counting only MariaDB's `mysql-test` tree gives (re-verified 2026-09-07 by
unpacking the official archive; no `git clone` of the GitHub repository is
required):

```sh
tar xzf mariadb-11.8.8.tar.gz
find mariadb-11.8.8/mysql-test -name '*.test' | wc -l
```

Result: `6650`. The Windows PowerShell equivalent against the same tree is
`(Get-ChildItem -Recurse -File mysql-test -Filter *.test | Measure-Object).Count`.

The same official archive contains `12339` files with the `.test` suffix in the
whole tree. The additional files are bundled dependency and plugin tests outside
the MariaDB `mysql-test` suite:

| Top-level directory | `.test` files |
|---|---:|
| `mysql-test` | 6650 |
| `storage` | 5500 |
| `plugin` | 163 |
| `extra` | 26 |
| **Whole archive** | **12339** |

Therefore `mysql-test/**/*.test` is reported as `6650`; the larger whole-archive
count is not the MariaDB `mysql-test` baseline.

## Execution status

The default Conan build produces the `minbuild` server and mysql-test driver
artifacts, then runs a real-device-verified serial subset of the upstream
`main` suite. The installed package remains focused on the client library and
client development artifacts:

- `WITHOUT_SERVER=False` (the default) builds the server artifacts needed for
  upstream validation, including `mariadbd` and `mariadb-test`;
- `without_server=True` remains available for client-only consumers;
- `WITH_UNIT_TESTS=False` avoids building the upstream test binaries.
- `package()` installs the client/development components and does not package
  the whole `mysql-test` tree.

`mysql-test-run` is a server integration harness. It starts a private
`mariadbd`, manages sockets, ports, and data directories, and uses the
`mariadb-test` driver. OHOS HMDFS rejects MariaDB's default file-backed Unix
socket, so the recipe uses a TCP-only harness configuration on loopback for
validation. This unlocks the complete `main` suite and the `binlog`/`client`
suites without changing upstream test semantics.

The one `test_package` executable is a consumer smoke test for linking and
calling the packaged client API. It is not counted as an upstream `mysql-test`
result.

## Reported result

On 2026-09-05, an OHOS real device executed the complete `main`, `binlog`, and
`client` boundaries. MTR discovered 1517 independent tests from 1533 `.test`
files, expanding to 1656 combinations. The final merged result was 1124 passed,
70 failed, 317 skipped, and 6 disabled.

The strict upstream pass rate is 1124/6650 (16.90%). File coverage is
1533/6650 (23.05%). Among executed non-skipped independent tests, the pass rate
is 1124/1194 (94.14%).

The recipe's CI gate runs 56 real-device-verified passing `main` cases after
every default full-server build. Full results, the 6650-file mapping, failure
triage, commands, and evidence paths are recorded in
`reports/mysql-test-ohos-full-run.md`.

## 5117-file classification

The 5117 unexecuted `.test` files split into exactly two classes at suite
granularity (per-suite counts re-derived 2026-09-07 from the official archive;
2204 + 2913 = 5117):

1. **Blocked by build configuration / topology / environment — 2913 files**:
   replication and wsrep-cluster topology (multi-server `mariadbd` farms,
   wsrep provider not compiled), `PLUGIN_PERFSCHEMA=NO`,
   `WITH_MARIABACKUP=False`, `PLUGIN_S3=NO`, dynamic-plugin suites whose
   `.so` targets are not part of the `minbuild` product (`encryption`,
   `plugins`, `federated`, `archive`), external engine-matrix suites
   (`engines`, `storage_engine`), upstream long-running stress, harness
   self-tests, shared includes, and the upstream known-unfixed-bugs
   collection. Each suite's specific blocking reason is tabulated in
   `reports/mysql-test-ohos-full-run.md`.
2. **Runnable but not executed — 2204 files**: single-server suites that only
   need the built-in engines already compiled into `mariadbd` (`sys_vars` 755,
   `innodb*` 592, `parts` 142, `funcs_1/2` 127, `jp` 111, `compat` 90,
   `maria` 66, `vcol`/`roles`/`gcol`/`versioning`/`sql_sequence`/`atomic`
   and the small engine suites). No platform or build blocker exists for
   these; they exceeded the serial single-device validation budget of the
   2026-09-05 runs. They are **not** claimed as passed, and they remain the
   incremental follow-up scope once a device is available again.
