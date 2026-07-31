# renattach 1.2.4 pre-adaptation notes

## Scope and issue

- Worktree: `D:/harmonyos/worktrees/renattach`
- Branch: `feat/renattach-1.2.4`
- Issue: #1605.
- This preparation changes `archives/r/renattach/1.2.4/` and the required
  software-level command declaration `archives/r/renattach/commands.json`.

## W0 dependency check

- Required third-party C/C++ dependencies: none.
- The signed Debian source descriptor declares only packaging/test tooling:
  `debhelper-compat`, `exim4 | mail-transport-agent`, and `procmail`.
  These are not linked by renattach and are not Conan requirements.
- The upstream source links only the platform C/POSIX runtime.
- Required dependency recipes to download from `ohpcd`: none.
- Target collision probe attempted:

  ```text
  conan download renattach/1.2.4 -r=ohpcd --only-recipe
  ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
  ```

  Retry this probe before PR/CI. The current result does not prove that the
  target version is absent from the registry.

## Source and build-system analysis

- Upstream homepage: `https://www.pc-tools.net/unix/renattach/`.
- Source archive: upstream release tarball
  `https://www.pc-tools.net/files/unix/renattach-1.2.4.tar.gz`.
- SHA-256: `05b6a7dfde17165a35cdb60a7909899bc8060cbc3468f06ce31745e285153155`.
- Build system: Autoconf/Automake (`configure.ac`, generated `configure`, and
  `Makefile.am`). It does not use `AC_CANONICAL_HOST`, `config.guess`, or
  `config.sub`, so no fake Linux host triplet is needed.
- Output: one C command-line program, `bin/renattach`; no libraries or headers.
- Installed data: `etc/renattach.conf.ex` and `share/man/man1/renattach.1`.
- External libraries: none. Source uses standard C/POSIX interfaces including
  `getopt_long`, `ftruncate`, `fork`, `pipe`, `execv`, and optional `syslog`.
- Upstream tests: zero. `make check` exists as an empty Automake target and is
  retained in `build()` for traceability.

## HarmonyOS adaptation

The main filter stores the whole message in `tmpfile()`. HarmonyOS runners
provide a writable job-local `TMPDIR`, while the platform default temporary
directory may not be writable in isolated sessions. Patch 0001 uses a portable
runtime check: when `TMPDIR` is set, it creates a private file there with
`mkstemp()`, immediately unlinks it, and wraps the descriptor with `fdopen()`;
when `TMPDIR` is unset, it falls back to the original `tmpfile()` behavior. No
platform conditional compilation is used.

HarmonyOS SSH validation also exposed two build-system issues:

- OpenSSH user sessions on HMDFS cannot reliably execute the unpacked
  `configure` script directly from Conan's cache, so the OHOS build path avoids
  Autotools' direct `configure` invocation.
- Old Autoconf 2.59 repeatedly failed in `config.status` with SSH-domain
  `getcwd`/temporary-file permission errors. Since renattach is a small CLI
  with three C sources and no external libraries, the OHOS recipe path generates
  the probed `config.h` values directly, compiles `src/renattach.c`,
  `src/settings.c`, and `src/utility.c` with the profile compiler, then
  manually packages `bin/renattach`, `etc/renattach.conf.ex`, and
  `share/man/man1/renattach.1`. The Linux path still uses Autotools.

The test package runs the installed executable, checks its version, filters a
multipart MIME message, and verifies that `virus.exe` becomes
`virus_exe.bad`, the filter metadata and subject are updated, and the payload
is preserved. It explicitly sets `TMPDIR`, so the portable temporary-file path
is exercised.

## Local validation boundary

The Windows host initially had no Conan, Python, CMake, Clang, or Make in
`PATH`. A temporary venv was prepared with the project-specified Conan 2.29.1
for recipe parsing and W0 probes.

Completed on 2026-07-28:

- Recomputed the 112566-byte source archive SHA-256 and matched `conandata.yml`.
- Parsed all three Python files and all three YAML files successfully.
- Ran `conan inspect`, `conan export`, and an OHOS/aarch64 `conan graph info`;
  the recipe exported its patch and the graph contained no dependencies.
- Ran `ohc-run.py resolve-deps renattach 1.2.4 --dry-run`; all dependencies
  were reported ready because the recipe has no third-party requirements.
- Applied the repository's static L0a-L0e/L0g-L0i/L0m/L0n checks manually;
  they pass. L0j remains unresolved.
- Ran `patch --dry-run -p1` against the original source; both hunks apply
  cleanly without offsets or fuzz.

This host still cannot perform the native OHOS/aarch64 compile or runtime
test: no compiler/build toolchain is available in `PATH`, and WSL distro
enumeration is denied. Do not mark this version built or published until the
single-package device/shadow CI run passes.

## HarmonyOS PC validation

Completed on 2026-07-29 via SSH to HarmonyOS PC; rerun after PR review fixes
on 2026-07-29:
`192.168.137.84:2222`:

```sh
cd "$HOME/validation/renattach/archives/r/renattach/1.2.4"
conan create . \
  -pr:h="$HOME/validation/renattach/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/validation/renattach/ci/conan/profiles/ohos-aarch64" \
  --build=missing \
  --build=renattach/*
```

Latest result:

- Recipe revision: `1fffef450db706bfdfc57e4a8d7ff1f2`.
- Package revision: `c889215c5595727d22bdbf50f8716d53`.
- Package folder:
  `$HOME/.conan2/p/b/renatf87a56ab8f783/p`.
- Packaged files: `bin/renattach`, `etc/renattach.conf.ex`,
  `share/man/man1/renattach.1`, and `licenses/COPYING`.
- `bin/renattach --version` prints `renattach 1.2.4`.
- `file bin/renattach` reports an aarch64 PIE executable for musl.
- `test_package` passed all eight assertions:
  version smoke test, MIME filtering exit status, renamed
  `Content-Type` filename, renamed `Content-Disposition` filename, filter
  metadata, subject marker, and safe payload preservation.

Validation log on the device:
`$HOME/validation/logs/renattach-conan-create-final.log`.

The project wrapper
`CI_PACKAGES="archives/r/renattach/1.2.4" zsh ci/conan/build_and_test.sh`
was also tried on the same validation worktree, but it exited during L0i before
normal L0 result reporting. `zsh -x` showed the early exit at the dependency
extraction assignment for this no-dependency recipe. No repository
infrastructure files were changed for this package.

## Next commands

Before PR submission, retry the registry collision probe in an environment
where the `ohpcd` remote policy is enabled:

```sh
conan download renattach/1.2.4 -r=ohpcd --only-recipe
```

Optional full wrapper/shadow CI command, once the wrapper environment is fixed
or available:

```sh
CI_PACKAGES="archives/r/renattach/1.2.4" zsh ci/conan/build_and_test.sh
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/r/renattach/1.2.4
```

Expected checks:

- Build Summary reports `Total: 1`.
- L0 and L1 pass; L2 passes because this is a CLI package.
- L4 patch scan passes and L5 finds `bin/renattach`.
- The test output contains eight `[ok]` assertions.
- Exercise `renattach --pipe` separately if full optional-feature coverage is
  required; it uses `fork`, `pipe`, and `execv` and is not covered here.

## PR follow-up

- The ohpcd target-version collision probe must succeed.
- Full project wrapper/shadow CI has not completed; direct HarmonyOS PC
  `conan create` and `test_package` passed.
- `archives/r/renattach/commands.json` is now added because renattach packages
  the `renattach` command-line tool.
