# tart 3.10 adaptation notes

## Scope

- Target library: tart
- Version: 3.10
- Issue: #1839
- Branch: feat/tart-3.10
- Worktree: D:\harmonyos\worktrees\tart
- Date: 2026-08-04

## W0 dependency check

No third-party Conan dependencies were identified from the upstream Autotools metadata. `configure.in` only checks libc/POSIX headers and functions:

- Headers: `fcntl.h`, `stdlib.h`, `string.h`, `sys/param.h`, `sys/wait.h`, `unistd.h`
- Functions: `alarm`, `strftime`, `sysinfo`
- Optional configure toggles: `--enable-color`, `--enable-ibeats`, `--with-length`

Result: W0 dependency publication check is clean; there are no dependency libraries to split into separate issues.

## Issue and version confirmation

GitCode issue #1839 is open and names `tart`, but the issue body does not specify a version. The earlier user-supplied `3.1` could not be matched to an official SourceForge source package:

- `LinuxTaRT-3.1.tar.gz` returned `404 Not Found`.
- SourceForge officially lists `3.10`, `3.09`, `3.08`, and `3.07`.

The target has now been corrected to `3.10`. The official 3.10 source URL is:

```text
https://sourceforge.net/projects/linuxtart/files/linuxtart/3.10/LinuxTaRT-3.10.tar.gz/download
```

SHA256:

```text
b4e4617088fa71998db5ccdfd060142b9c74bf779f8164367e073714035c2bcb
```

## Build system analysis

LinuxTaRT 3.10 is an old Autotools project. The release archive contains:

- `configure`
- `configure.in`
- `config.h.in`
- `Makefile.in`
- `src/Makefile.in`
- `doc/Makefile.in`
- `misc/Makefile.in`

`src/Makefile.in` builds a single executable `tart` from:

- `main.o`
- `stringutil.o`
- `tartutil.o`
- `riscos.o`
- `IniFile.o`
- `ibeat.o`

The upstream install rule uses:

```make
install -s -D tart $(bindir)/tart
```

Because `install -D` may not be available on OHOS, `conanfile.py` packages by manual copy instead of running `make install`.

## Conan recipe

Prepared files:

- `conandata.yml`
- `conanfile.py`
- `test_package/conanfile.py`
- `test_package/MANIFEST.yml`
- `commands.json`

Recipe choices:

- `AutotoolsToolchain` for environment generation, then explicit `sh ./configure` and `make -j1`.
- `validate()` allows only `Linux` and `OHOS`.
- Configure args:
  - `--prefix=/`
  - `--enable-color=no`
  - `--disable-ibeats`
- No upstream test suite is run during build because upstream does not provide an automated test target.
- `conandata.yml` sets `filename` explicitly because the SourceForge URL ends in `/download`.
- `build()` invokes `sh ./configure` explicitly to avoid direct `configure` execution failures on OHOS.
- The old Autoconf script uses `umask 077` for `confstat*` directories; on the OHOS test filesystem that creates unwritable temporary directories, so the recipe rewrites it to `umask 022` before configure.
- Package contents:
  - `bin/tart`
  - `licenses/COPYING`
  - man pages under `share/man`
  - sample config/tagline files under `share/tart`

## test_package

The test package exercises the installed executable:

- Runs `tart --help` and checks for `LinuxTaRT`.
- Runs `tart --license` and checks for GPL notice.
- Creates a temporary `.tartrc` and custom template, then runs `tart --config <temp>/.tartrc +cust +q -sd`.
- Asserts the configured signature file is created and includes expected content.
- Disables special-date lookup explicitly with `-sd` to avoid the upstream EOF handling issue in special date files.
- Cleans the temporary directory in `finally`.

## Local validation

Completed locally:

- Renamed branch to `feat/tart-3.10`.
- Confirmed official SourceForge 3.10 URL returns a downloadable `LinuxTaRT-3.10.tar.gz`.
- Re-downloaded source and verified SHA256.
- Confirmed `.tartrc` key names from upstream source and man page.
- Prepared recipe, source metadata, test_package, manifest, notes, and commands.json.
- Static checks passed: `commands.json` JSON parsing, Python AST parsing for recipe/test_package, `git diff --check`, and whitespace scan.

Completed on OHOS device:

- Host: `currentUser@10.62.189.79:2222`
- Command: `CI_PACKAGES="archives/t/tart/3.10" zsh ci/conan/build_and_test.sh`
- RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/tart-3.10-20260805003309`
- Result: exit code 0.
- Gates: L0/L1/L2/L4/L5 passed.
- Evidence: `conan create` passed, `test_package` executed, destructive negative test confirmed the test depends on `tart`, `tart --help` smoke passed, and `ci-metadata.json` was generated.

Not completed:

- `conan create`: local Windows environment has no `conan`.
- `patch --dry-run`: no patches were added; local Windows environment has no `patch`.
- Shell build: local `bash` fails with WSL `E_ACCESSDENIED`.

## Next command

If re-running the single package on OHOS/shadow CI:

```sh
CI_PACKAGES="archives/t/tart/3.10" zsh ci/conan/build_and_test.sh
```
