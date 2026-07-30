# mpfr 4.2.2 HarmonyOS adaptation notes

## Status

- Date: 2026-07-30
- Branch: feat/mpfr-4.2.2
- Issue: pending; no explicit issue number was found in the local project files or delegated context.
- Conan remote status: `gmp/6.3.0` is published in `ohpcd` with an OHOS armv8 static binary; `mpfr/*` is not published yet.
- Current state: standard Conan recipe and non-empty `test_package` prepared and validated by OHOS single-package runner r7. Ready for issue/PR follow-up and publish validation.

## Source And Build System

- Source: `https://ftp.gnu.org/gnu/mpfr/mpfr-4.2.2.tar.xz`
- SHA256: `b67ba0383ef7e8a8563734e2e889ef5ec3c3b898a01d00fa0a6869ad81c6ce01`
- Build system: Autotools (`configure.ac`, release `configure`, `Makefile.am/in`)
- Required dependency: `gmp/6.3.0`
- Upstream validation: `make check -j1`

## Recipe

The recipe uses Conan 2 `AutotoolsToolchain` and `Autotools`. It passes GMP include and library directories from the Conan dependency into MPFR configure through `--with-gmp-include` and `--with-gmp-lib`, avoiding manual `CPPFLAGS`, `LDFLAGS`, `LD_LIBRARY_PATH`, or `PKG_CONFIG_PATH` setup. Shared/static mode and static fPIC are controlled by Conan options.

## Patches

| Patch | Purpose |
|---|---|
| `0001-config.guess.patch` | Add direct HarmonyOS uname recognition and return `*-unknown-linux-ohos` without the Linux libc temp-file probe. |
| `0002-config.sub.patch` | Accept `linux-ohos` triples during Autotools canonicalization. |
| `0003-configure-tmpdir.patch` | Use `${TMPDIR:-.}` and `umask 022` for `config.status` temp directories to avoid HarmonyOS user-storage ACL denial on generated awk files. |

## Test Package

`test_package` builds a C executable with CMakeDeps/CMakeToolchain, consumes the tested `mpfr` reference plus `gmp/6.3.0`, initializes an MPFR value, multiplies 21 by 2, checks the MPFR integer comparison, checks the double result, and prints the MPFR version. GMP is declared explicitly in the test package and its target include directories are added to the test target so `mpfr.h` can include `gmp.h` reliably in OHOS CMakeDeps builds.

## Local Validation

Commands run on the Windows host:

```sh
conan search "gmp/*" -r=ohpcd
conan list "gmp/6.3.0:*" -r=ohpcd
conan search "mpfr/*" -r=ohpcd
conan source <temp-copy-of-recipe>
conan export archives/m/mpfr/4.2.2
conan graph info archives/m/mpfr/4.2.2 -s os=Linux -s arch=x86_64 -s compiler=gcc -s compiler.version=13 -s compiler.libcxx=libstdc++11 -s build_type=Release --build=never -r=ohpcd
```

Results:

- `gmp/6.3.0` recipe and OHOS armv8 static package exist in `ohpcd`.
- `mpfr/*` search returned no matching recipe in `ohpcd`.
- Conan `source()` downloaded the official tarball, verified sha256, unpacked into `src/`, and applied all three patches.
- OHOS runner note: use the GNU canonical `/gnu/mpfr/` source path so the CI mirror fallback rewrites to valid `/gnu/mpfr/...` mirror paths.
- OHOS permission probe: `umask 077 && mktemp -d "$HOME/tmp/confXXXXXX"` creates a directory where `config.status` cannot write/read `subs1.awk`; `umask 022` on the same path allows the generated awk machinery to run.
- `config.guess` now handles `HarmonyOS` directly instead of entering the Linux libc probe, avoiding the same `$HOME/tmp` permission denial for `dummy.c`.
- Temporary Conan cache export succeeded for `mpfr/4.2.2`.
- Conan graph resolution succeeded and resolved the direct `gmp/6.3.0` dependency.
- Full local Autotools build was not run on the Windows host because `sh`, `make`, `cmake`, and clang are not available in this environment.

## OHOS Device Validation

Single-package runner command used on 2026-07-30:

```sh
sh $HOME/bin/ohos-test-runner.sh --user codex-mpfr --lib mpfr --task mpfr-4.2.2-conan-r7 --mode heavy --try-lock --workdir /storage/Users/currentUser/ohos-users/codex-mpfr/mpfr-4.2.2-20260730-1228/repo/build_in_harmonyos -- sh /storage/Users/currentUser/ohos-users/codex-mpfr/mpfr-4.2.2-20260730-1228/run-mpfr-ci.sh
```

Results:

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-mpfr-mpfr-mpfr-4.2.2-conan-r7-20260730-132332-45286`
- Exit code: `0`
- Full package reference: `mpfr/4.2.2#1bb5a74372e0802ea1e8414798a2f9bb:504014e02a7e90aad722612f5b3526cd5f20316b#37d778fa8956640cca6cbfad85116a04`
- Upstream `make check`: `TOTAL=198`, `PASS=195`, `SKIP=3`, `FAIL=0`, `ERROR=0`
- Conan `test_package`: CTest `1/1` passed, then explicit `./test_mpfr` printed `MPFR 4.2.2 result: 42.0`
- Runner checks: `L0=pass`, `L1=pass`, `L2=skip` (no `bin/` directory), `L4=pass`, `L5=pass`
- Build summary: `Total=1`, `Success=1`, `Failed=0`

## Next Commands.

Shadow/PR CI command to run after the issue/PR is ready:

```sh
CI_PACKAGES="archives/m/mpfr/4.2.2" zsh ci/conan/build_and_test.sh
```
