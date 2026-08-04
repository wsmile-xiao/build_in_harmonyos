# pick 2.0.2 adaptation notes

## Status

Built and verified on the OHOS real-device worker after the R19 cleanup. The final recipe replaces the bundled binary artifact with a source-built fallback and moves Autotools/test-runner edits into declared patches.

## Build approach

- Source: GitHub release tarball `pick-2.0.2.tar.gz`.
- Upstream build system: Autotools.
- Recipe strategy: inject `DEFAULT_PREFIX/include`, `DEFAULT_PREFIX/include/ncursesw`, `DEFAULT_PREFIX/lib`, and `PKG_CONFIG_PATH`; fall back to bundled ncurses headers and a terminfo compatibility archive built from `res/src/pick_terminfo.c` during `build()`.
- `config.guess`, `config.sub`, `configure`, `Makefile.in`, and the Automake test runner are patched through declared `conandata.yml` patches.
- OHOS uses a job-local shell for `configure` and for the upstream Automake `.t` test runner because system shell shebang execution is denied in this worker.
- The upstream test script sets `TMPDIR` to a writable build directory when the runner environment does not provide one.
- The recipe keeps a GitHub API asset fallback because the direct release asset URL timed out during local source inspection.

## Dependencies

- ncurses-compatible headers plus the source-built terminfo subset fallback supplied from `res/` in this archive

## Verification

- OHOS new port `33332`, runner mode `heavy`.
- Final run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-2.0.2-pick-pr3564-selfcopy-20260801-r2-conan-20260801-231029-52987`.
- Full package ref: `pick/2.0.2#f57da04dc87068619a6da04148f21c7c:6b129b068851896169fae42d399fa922d239ce8a#f8a2e555e9aa4e6cc2360745978285be`.
- `conan create` and `test_package` passed. `test_package` verifies `pick -v` returns `2.0.2`.
- Runner gates in that run: L0 pass, L1 pass, L2 skip because the generic `--version/--help` check does not match this CLI, L4 pass, L5 pass, L1e pass.
- Upstream `make check` was executed in that run. Result: 33/33 pass; see `reports/upstream-tests.md`.
- Local `py_compile`, patch apply checks, fallback C compile, and Conan export/source-stage checks pass.

Windows is rejected by `validate()` because this package requires POSIX terminal APIs and ncurses.
