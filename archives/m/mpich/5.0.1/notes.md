# mpich 5.0.1 adaptation notes

## Scope

- Library: mpich
- Version: 5.0.1
- Branch: feat/mpich-5.0.1
- Worktree: D:\harmonyos\worktrees\mpich-5.0.1
- Issue: TODO, no explicit issue number was found in project files, mpich 4.0.3 context, or current task context.

## W0 dependency check

`conan download "mpich/5.0.1" -r=ohpcd --only-recipe` fails with:

```text
error:system acceleration policy not enabled. [Remote: ohpcd]
```

`conan download "perl/5.42.2" -r=ohpcd --only-recipe` previously failed with the same remote policy error. After rebasing onto `origin/main` on 2026-07-30, `archives/p/perl/5.42.2/conanfile.py` is present in main.

MPICH 5.0.1 upstream `configure` still requires Perl. The mpich recipe now declares `tool_requires("perl/5.42.2")` when the build context is Linux or OHOS. It intentionally skips the tool requirement for Windows build-context graph parsing, because the Perl recipe validates only Linux/OHOS native builds.

Using the project profile `ci/conan/profiles/ohos-aarch64`, Conan resolves Perl from `ohpcd`:

```text
perl/5.42.2#13c4f5bde5668df0b7268c4d0c01073c:6b129b068851896169fae42d399fa922d239ce8a#ec97109d67c453b723126b261da3fd9e - Download (ohpcd)
```

## Source and build system

- Source URL used by recipe: https://github.com/pmodels/mpich/releases/download/v5.0.1/mpich-5.0.1.tar.gz
- Official source URL: https://www.mpich.org/static/downloads/5.0.1/mpich-5.0.1.tar.gz
- SHA256: `8c1832a13ddacf071685069f5fadfd1f2877a29e1a628652892c65211b1f3327`
- Build system: Autotools (`configure`, `configure.ac`, `Makefile.in`)
- Upstream tests: large MPI suite under `test/mpi`, plus examples such as `examples/cpi.c`.

The official `www.mpich.org/static` URL is currently blocked from this Windows host by a Cloudflare JavaScript challenge, so the recipe uses the matching GitHub release asset. The Git tag auto-archive has a different sha256 and is not used.

## Recipe strategy

The recipe starts with a minimal local C MPI surface:

- `--with-device=ch3:sock`
- `--with-pm=gforker`
- `--with-pmi=pmi1`
- `--with-pmilib=install`
- `--disable-fortran`
- `--disable-cxx`
- `--disable-romio`
- `--with-hwloc=no`
- `--with-wrapper-dl-type=none`
- `--with-datatype-engine=dataloop`

This keeps the first 5.0.1 package focused on C MPI consumers (`mpicc`, `mpiexec`, `libmpi`) and avoids pulling libfabric, UCX, hwloc, Fortran, Yaksa, and MPI-IO into this PR.

The recipe borrows the HarmonyOS platform guards proven during mpich 4.0.3:

- call `configure` through an available shell instead of direct script execution
- set `TMPDIR` and `TMPPREFIX` under the build folder
- override broken `SHELL` and `CONFIG_SHELL`
- fall back from unavailable profile compiler paths to `PATH` tools
- wrap `/bin/sh` shebang compiler scripts with the selected shell
- relax Autoconf `umask 077` temporary directories to `umask 002`
- pass `llvm-ar`, `llvm-ranlib`, `llvm-nm`, and `ld.lld` when available

## Verification performed locally

- Created isolated worktree `D:\harmonyos\worktrees\mpich-5.0.1` on branch `feat/mpich-5.0.1`.
- Confirmed existing `D:\harmonyos\worktrees\mpich` is the separate mpich 4.0.3 worktree and was not modified.
- Searched local project files and prior mpich 4.0.3 task context; found only pnetcdf references to `mpich/4.0.3`, no explicit issue number for `mpich/5.0.1`.
- Rebased the mpich worktree onto `origin/main` after Perl 5.42.2 landed.
- Downloaded the GitHub release source asset and computed sha256.
- Inspected source layout and configure options.
- Prepared Conan recipe and non-empty `test_package`.
- `ast.parse` passed for `conanfile.py` and `test_package/conanfile.py`.
- YAML parsing passed for `conandata.yml`, `manifest.yaml`, and `test_package/MANIFEST.yml`.
- `conan inspect archives\m\mpich\5.0.1` loaded recipe metadata successfully.
- `conan graph info archives\m\mpich\5.0.1` with explicit OHOS 6.0 armv8 clang-15 host settings and Windows build settings parsed with no dependencies and `info_invalid: None`.
- `conan graph info archives\m\mpich\5.0.1 -pr:h=ci\conan\profiles\ohos-aarch64 -pr:b=ci\conan\profiles\ohos-aarch64 --format=json` resolved `perl/5.42.2` from `ohpcd` as a downloadable build requirement.
- Main worktree remained on its current Apache Arrow branch and was not modified.

## Deferred device/shadow CI commands

This round intentionally did not start device/shadow CI because the user requested local pre-adaptation unless an explicit idle device window is available.

After a Perl-capable build environment is available, run the single-package validation:

```sh
CI_PACKAGES="archives/m/mpich/5.0.1" zsh ci/conan/build_and_test.sh
```

If using the shadow CI wrapper:

```sh
/path/to/run-ohos-shadow-ci.sh archives/m/mpich/5.0.1
```

If the build reaches runtime testing, confirm:

- `mpicc -show` prints wrapper compile/link flags.
- `mpiexec -n 2 ./test_mpi` launches two local ranks.
- `MPI_Allreduce` and `MPI_Get_library_version` smoke assertions pass.

## Second-device queued build

On 2026-07-30, the second HarmonyOS device was reachable through Sakura
`frp-tip.com:33332`; direct `10.62.228.146:2222` timed out from this host.

Prepared isolated job:

```text
/storage/Users/currentUser/ohos-users/codex-mpich501/mpich-5.0.1-20260730-211651
```

The local `archives/m/mpich/5.0.1` directory was synced into the isolated repo
with tar sha256 `9be0367803aa5081cd9f0f82b1d620df584e60a2dfd4ecfcdc278ae37f893210`.

The second device was not idle: an existing `ninja_test` process from
`codex-a/ninja-build-1.13.2-newport-split-r1` was still consuming 100% CPU after
more than three hours. To respect the single-heavy-job queue, a background
waiter was started at:

```text
/storage/Users/currentUser/ohos-users/codex-mpich501/mpich-5.0.1-20260730-211651/start-after-idle.sh
```

It logs to:

```text
/storage/Users/currentUser/ohos-users/codex-mpich501/mpich-5.0.1-20260730-211651/logs/queued-start.log
```

The blocking `ninja_test` process was later confirmed to belong to the
`codex-a` isolated job for `archives/n/ninja-build/1.13.2`:

```text
/storage/Users/currentUser/ohos-users/codex-a/ninja-build-1.13.2-newport-split-r1
```

It was stuck in `SubprocessTest.SetWithLots` and repeatedly logged
`ninja: ppoll: Out of memory`. After user approval, PID `47724` was terminated
with `kill -9`, allowing mpich to start.

The first mpich run failed before source build because the isolated Conan home
had a stale/generated `settings.yml` without `OHOS`. The job-local
`settings.yml` was patched to include `OHOS.version=6.0`, then the heavy runner
was restarted.

Active/most recent run:

```text
/storage/Users/currentUser/ohos-test-runs/codex-mpich501-5.0.1-mpich-5.0.1-20260730-211651-conan-20260730-214735-28003
```

This run reached `mpich/5.0.1: Calling build()` after downloading
`perl/5.42.2` from `ohpcd` and unpacking the MPICH source.

That run then failed in `configure` because MPICH 5.0.1 no longer accepts
`--with-pmi=simple` as an internal PMI selector; it treated the value as an
external PMI path and failed to find `pmi.h`/`libpmi`. `configure --help` lists
`pmi1`, `pmi2`, and `pmix`, so the recipe was updated to use `--with-pmi=pmi1`
with `--with-pmilib=install`.

The rerun with the PMI fix completed `configure`, `make -j1`, and upstream
`make install`, installing `libmpi.so.12.6.1`, `mpiexec`, and wrapper tools into
the Conan package folder. It then failed in `package()` because the recipe used
the unsupported Conan 2 call `copy(..., delete=True)` while trying to remove
libtool files. The recipe now uses `rm()` to delete `*.la`/`*.dylib` from
`lib/`.

The next full second-device run completed `configure`, `make -j1`, upstream
`make install`, and `package()`. It proved that the package-stage wrapper patch
works: `mpicc test.c -o test_mpi` succeeded and `mpicc -show` printed package
local include/lib paths. That run then failed only because the test package
passed a malformed quoted command to `/system/bin/sh -c`.

After fixing the test package quoting and adding `TMPDIR`/`TMPPREFIX` for the
test build, a targeted second-device validation against the already built cache
package passed:

```sh
conan test archives/m/mpich/5.0.1/test_package \
  "mpich/5.0.1#b6331af64559c98bb992f74498d17509" \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=never
```

The targeted test compiled with `mpicc`, ran `mpicc -show`, then launched:

```sh
MPIEXEC_TIMEOUT=30 mpiexec -n 2 ./test_mpi
```

The smoke test reported two ranks and `MPICH Version: 5.0.1` with
`MPICH Device: ch3:sock`.

Final full second-device validation also passed:

```text
/storage/Users/currentUser/ohos-test-runs/codex-mpich501-5.0.1-mpich-5.0.1-20260730-211651-conan-20260730-235509-53226
```

Runner timestamps:

```text
[2026-07-30T15:55:10Z] start
[2026-07-30T16:25:05Z] end rc=0
```

The full run rebuilt `mpich/5.0.1`, created package revision
`c0697a694c407e852709df116966b2d9`, compiled the test package with the packaged
`mpicc`, showed package-local wrapper flags, and ran `mpiexec -n 2 ./test_mpi`
successfully on the device.
