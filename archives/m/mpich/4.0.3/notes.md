# mpich 4.0.3 adaptation notes

## Scope

- Library: mpich
- Version: 4.0.3
- Branch: feat/mpich-4.0.3
- Worktree: D:\harmonyos\worktrees\mpich
- Issue: #1693

## W0 dependency check

`conan download "mpich/4.0.3" -r=ohpcd --only-recipe` still fails with:

```text
error:system acceleration policy not enabled. [Remote: ohpcd]
```

This package has one configure-time tool dependency:

- `perl/5.42.2`

The local pnetcdf metadata references `mpich/4.0.3`, but that record describes a manually installed MPI and does not provide a Conan-consumable recipe.

## Source and build system

- Source URL: https://www.mpich.org/static/downloads/4.0.3/mpich-4.0.3.tar.gz
- SHA256: `17406ea90a6ed4ecd5be39c9ddcbfac9343e6ab4f77ac4e8c5ebe4a3e3b6c501`
- Build system: Autotools (`configure`, `configure.ac`, `Makefile.in`)
- Upstream tests: large MTest MPI suite under `test/mpi`, plus examples such as `examples/cpi.c`.

## Recipe strategy

The recipe intentionally starts with a minimal local MPI surface:

- `--with-device=ch3:sock`
- `--with-pm=gforker`
- `--with-pmi=simple`
- `--disable-fortran`
- `--disable-cxx`
- `--disable-romio`
- `--with-hwloc=no`
- `--with-wrapper-dl-type=none`

This keeps the first MPICH package focused on C MPI consumers (`mpicc`, `mpiexec`, `libmpi`) and avoids pulling libfabric, UCX, hwloc, Fortran, and MPI-IO into this PR.

The recipe declares `perl/5.42.2` as `tool_requires` because MPICH upstream configure requires a Perl interpreter even with Fortran/C++/ROMIO disabled.

Because the package installs command-line wrappers such as `mpicc` and `mpiexec`, the software-level `archives/m/mpich/commands.json` declares MPICH as a tool package for R38 metadata checks.

## Verification performed locally

- Downloaded the official source tarball and computed sha256.
- Inspected source layout and configure options.
- Prepared Conan recipe and non-empty `test_package`.
- `ast.parse` passed for `conanfile.py` and `test_package/conanfile.py`.
- YAML parsing passed for `conandata.yml`, `manifest.yaml`, and `test_package/MANIFEST.yml`.
- `conan inspect` loaded the recipe metadata successfully.
- `conan graph info` with an explicit temporary OHOS 6.0 armv8 clang-15 profile parsed with no dependencies and `info_invalid: None`.
- Device execution was later authorized and run through the isolated heavy runner.

`reports/local-precheck.md` contains the same local checklist, but `reports/` is ignored by the repository's global `.gitignore`; force-add it only if the PR policy requires reports to be committed.

## Device validation performed

Device availability was checked before each run:

- global lock: free before mpich runs; free after the final run
- active process scan: no active `conan`, `cmake`, `ninja`, `mpiexec`, `open-mpi`, `hdf5`, `arrow`, `qtquick3d`, or `build_and_test` task found
- isolated job: `/storage/Users/currentUser/ohos-users/codex-mpich/mpich-4.0.3-F72D-20260726-1250`
- command: `zsh ci/conan/build_and_test.sh archives/m/mpich/4.0.3` via `run-conan-heavy.sh`
- latest run log: `/storage/Users/currentUser/ohos-test-runs/codex-mpich-4.0.3-mpich-4.0.3-F72D-20260726-1250-conan-20260726-133703-36128`

The recipe was iterated on-device past the initial runner/environment blockers:

- isolated `CONAN_HOME` needed the device `settings.yml` with `OHOS`
- `/storage` script execution required invoking `configure` through an available shell
- `/tmp` is not usable; `TMPDIR`/`TMPPREFIX` are set under the build folder
- profile tool paths pointed at unavailable `/data/service/hnp/bin/*`; recipe falls back to user toolchain wrappers
- wrapper scripts using `/bin/sh` shebang need shell wrapping or shebang rewriting
- Autoconf `umask 077` temporary directories fail on HMDFS; recipe relaxes generated configure scripts to `umask 002`
- `llvm-ar`, `llvm-ranlib`, `llvm-nm`, and `ld.lld` are injected explicitly

2026-07-26 blocker:

```text
configure: error: Perl is required but not found.
```

Confirmed on device at that time: `perl`, `perl5`, and `miniperl` were not present in the runner PATH or under `$HOME` within the searched depth.

2026-07-31 follow-up:

- Perl has since landed in `origin/main` as `archives/p/perl/5.42.2`.
- `mpich` now declares `self.tool_requires("perl/5.42.2")`.
- The older device validation snapshot still lacks the full Perl recipe, so isolated validation must use an updated repo snapshot or copy the complete `archives/p/perl/5.42.2` recipe from `origin/main` into the isolated job before rerunning mpich.

2026-07-31 device rerun:

- latest run log: `/storage/Users/currentUser/ohos-test-runs/codex-mpich-4.0.3-mpich-4.0.3-F72D-20260726-1250-conan-20260731-191414-15362`
- `perl/5.42.2` was already available in the isolated Conan cache.
- configure passed the previous `confdb/config.rpath` execution failure after running helper scripts through `CONFIG_SHELL`.
- configure emitted a non-fatal `/bin/bash` shebang warning from `test/mpi/maint/gentests_dtp.sh`; the recipe now rewrites `/bin/bash` shebangs as well as `/bin/sh`.
- `make -j1` and `make install` completed, then `package()` failed because Conan 2.29 `copy()` does not support `delete=True`.
- The recipe now uses `rm()` for unwanted `*.la`/`*.dylib` files, rewrites MPI wrapper prefixes to the package root, and uses `make -j2` to leave more room under the runner's 45-minute `conan create` timeout.

2026-07-31 later device rerun:

- latest run log: `/storage/Users/currentUser/ohos-test-runs/codex-mpich-4.0.3-mpich-4.0.3-F72D-20260726-1250-conan-20260731-201145-43271`
- `configure`, `make -j2`, `make install`, and `package()` completed successfully.
- Conan created package revision `3440a6aca67a6ce3b9cd1651e38ebaba`.
- `test_package` built the smoke executable and `mpicc -show` printed wrapper compile/link flags.
- Runtime smoke failed only at shell command construction: nested quoting produced `bash: -c: line 1: unexpected EOF while looking for matching '"'` before `mpiexec` ran.
- `test_package/conanfile.py` now uses `shlex.quote()` for the shell and `mpiexec` command; rerun is needed to confirm `mpiexec -n 2 ./test_mpi`.

2026-07-31 final device rerun:

- run log: `/storage/Users/currentUser/ohos-test-runs/codex-mpich-4.0.3-mpich-4.0.3-F72D-20260726-1250-conan-20260731-205442-65315`
- runner lock was acquired immediately and released cleanly; `exit-code.txt` is `0`.
- `configure`, `make -j2`, `make install`, `package()`, and `test_package` all completed.
- Conan package reference: `mpich/4.0.3#2f5051f70683e9bd24eda45c6da0dc23:01d92cf349a0dd98ff915f4bd99a04430171517f#70e4746e9183c28cbc41cdc90ae4f064`.
- `test_package` built the C smoke with packaged `mpicc`, printed `mpicc -show`, and ran `mpiexec -n 2 ./test_mpi`.
- Runtime smoke output included `mpich smoke: 2 ranks`, `MPICH Version: 4.0.3`, and `MPICH Device: ch3:sock`.
- CI wrapper summary: `Total: 1`, `Success: 1`, `Failed: 0`.
- L1 passed, L5 confirmed `bin/` content, L1e negative test confirmed the smoke genuinely depends on packaged `bin/`, `lib/`, and `include/`.
- L2 passed through `mpicc --version`; `mpichversion`, `mpiexec`, `mpivars`, and `parkill` version/help probes warned but were non-blocking.
- Software-level `archives/m/mpich/commands.json` was added and synced to the device after the active run had started; rerun from a clean start if an explicit L0k `commands.json valid (type=tool)` line is required in the final CI log.

## Upstream test/mpi validation

2026-08-01 device upstream run:

- primary run log: `/storage/Users/currentUser/ohos-test-runs/codex-mpich-4.0.3-mpich-4.0.3-upstream-testing-only-20260801-003944-62810`
- TAP: `/storage/Users/currentUser/ohos-users/codex-mpich/mpich-4.0.3-F72D-20260726-1250/conan-home/p/b/mpichd6500609e0297/b/build-release/upstream-test-build-manual3-20260801-002828/summary-ohos-upstream-rerun.tap`
- JUnit: `/storage/Users/currentUser/ohos-users/codex-mpich/mpich-4.0.3-F72D-20260726-1250/conan-home/p/b/mpichd6500609e0297/b/build-release/upstream-test-build-manual3-20260801-002828/summary-ohos-upstream-rerun.junit.xml`
- result summary: `62 tests failed out of 1958`
- TAP plan/counts: `1..1977`, `ok=1915` including `skip=19`, `not ok=62`
- pass-rate basis for PR: `1896/1958 (96.83%)`, excluding skipped cases from the denominator

The selected upstream suite covered `attr`, `coll`, `comm`, `datatype`, `errhan`, `group`, `info`, `init`, `mpi_t`, `pt2pt`, `part`, `rma`, `spawn`, `topo`, `errors`, and `impls`. C++/Fortran/ROMIO/threads coverage is excluded by this first minimal C-only package configuration.

Known failing groups:

- `datatype/vecblklen` and `datatype/hvecblklen`: byte-value mismatch, expected `0xff` but the program reports `-1`.
- `part/*`: partitioned communication tests such as `start_pready*`, `parrived*`, `multipart`, `nonblocking_pready`, `no_start`, and many `pingping` variants fail quickly, often with interrupted/segfaulted ranks.
- `spawn/namepub` and `errors/spawn/{unpub,lookup_name}`: name service commands return `unknown cmd ...` and then time out.

Remainder verification was also run to confirm the overlapping failure set from `datatype` onward:

- run log: `/storage/Users/currentUser/ohos-test-runs/codex-mpich-4.0.3-mpich-4.0.3-upstream-remainder-20260801-024421-64599`
- result summary: `62 tests failed out of 828`
- TAP counts: `1..847`, `ok=785` including `skip=19`, `not ok=62`
- This result is not added to the PR pass-rate denominator because it intentionally overlaps the primary run.

## Deferred device/shadow CI commands

For a clean shadow CI rerun:

```sh
CI_PACKAGES="archives/m/mpich/4.0.3" zsh ci/conan/build_and_test.sh
```

If direct Conan smoke is needed inside the worktree:

```sh
cd archives/m/mpich/4.0.3
conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```

If the scheduled upstream suite is needed from Conan, set `MPICH_RUN_UPSTREAM_TESTS=1`. The recipe also accepts `MPICH_UPSTREAM_TESTDIRS` or `MPICH_UPSTREAM_TESTLIST` to split heavy runs.

If the first build reaches runtime testing, confirm:

- `mpicc -show` prints wrapper compile/link flags.
- `mpiexec -n 2 ./test_mpi` launches two local ranks.
- `MPI_Allreduce` and `MPI_Get_library_version` smoke assertions pass.
