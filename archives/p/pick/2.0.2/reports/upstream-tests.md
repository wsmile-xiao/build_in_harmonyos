# pick 2.0.2 upstream test handling

Date: 2026-08-01

## Inventory

- Release source: `tests/*.t`, `tests/pick-test.sh`, and `tests/pick-test.c`.
- Upstream build integration: Autotools `make check`.
- Count: 33 `.t` tests registered by `TESTS` in `Makefile.am`.
- Test helper: `tests/pick-test.c` creates a pseudo terminal with
  `posix_openpt`, `grantpt`, `unlockpt`, and `TIOCSCTTY` so `pick` runs as an
  interactive terminal program.

Registered tests:

`key-alt-enter`, `key-backspace`, `key-ctrl-a`, `key-ctrl-c`,
`key-ctrl-e`, `key-ctrl-k`, `key-ctrl-l`, `key-ctrl-o`, `key-ctrl-u`,
`key-ctrl-w`, `key-del`, `key-end`, `key-enter`, `key-home`, `key-left`,
`key-line-down`, `key-line-up`, `key-page-down`, `key-page-up`,
`key-printable`, `key-right`, `key-unknown`, `misc-match`, `misc-realloc`,
`opt-d`, `opt-h`, `opt-k`, `opt-o`, `opt-q`, `opt-s`, `opt-unknown`,
`opt-v`, `opt-x`.

## OHOS handling

The upstream assertions were not changed. The recipe performs two test harness
environment fixes before running `make check`:

- Automake `T_LOG_COMPILER` invokes `tests/pick-test.sh` through
  `CONFIG_SHELL`, because direct shell script execution may be denied in OHOS
  workers.
- `tests/pick-test.sh` gets a writable `TMPDIR` fallback under the build
  directory, avoiding the read-only `/tmp` mount.

## OHOS execution status

- SSH port: new port `33332`.
- Runner mode: `heavy`.
- Final run_dir:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.0.2-pick-pr3564-selfcopy-20260801-r2-conan-20260801-231029-52987`.
- Full package reference:
  `pick/2.0.2#f57da04dc87068619a6da04148f21c7c:6b129b068851896169fae42d399fa922d239ce8a#f8a2e555e9aa4e6cc2360745978285be`.

Upstream `make check` was executed during the Conan build phase:

- Total: 33
- Passed: 33
- Failed: 0
- Skipped: 0
- Errors: 0

The current source-built fallback supplies the key and numeric terminfo
capabilities required by the upstream `.t` tests, including `khome`, `kend`,
and `tigetnum("cols"/"lines")`.

## Adapted package verification

The recorded OHOS `conan create` run succeeded for the final source-built
fallback recipe. It executed `make check` and the Conan `test_package`, which
executes the packaged binary and verifies that `pick -v` prints `2.0.2`.

Runner gates from the final run:

- L0: pass
- L1: pass, upstream `make check` and `test_package` both executed
- L2: skip, generic `--version/--help` probe does not match this CLI
- L4: pass
- L5: pass
- L1e: pass, destructive negative test confirms `test_package` depends on
  the packaged `pick` binary
