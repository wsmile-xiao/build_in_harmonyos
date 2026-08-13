# Smaller C 1.0.2 HarmonyOS adaptation notes

## Scope

- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2049
- Upstream: https://github.com/alexfru/SmallerC
- Release snapshot: `b120a9c389146bc2049dfff5fa16673210c8a12a`
- Build system: GNU Make
- Package type: compiler toolchain (`smlrc`, `smlrl`, `smlrcc`, `smlrpp`, and `n2f`)

The 1.0.2 release archive used by other distributions identifies the snapshot as
`b120a9c`. The recipe pins that snapshot to its full Git commit and records the
SHA256 of GitHub's codeload archive.

## Source and build analysis

The top-level `GNUmakefile` includes `common.mk`. It compiles five host utilities
with `CC`, then uses the newly built `smlrcc` plus NASM to regenerate seven x86
target standard libraries and `dpstub.exe`.

The repository's `ohos-aarch64` profile uses OHOS/aarch64 for both build and host,
so the formal device build is native and can execute the freshly produced
`smlrcc`. The recipe therefore keeps upstream's full `make all` flow and packages
the newly generated libraries and stub; committed prebuilt files under
`v0100/lib` are not used as package artifacts.

At runtime, `smlrcc` finds its headers and target libraries through the `SMLRC`
environment variable. `package_info()` sets `SMLRC=<package>/smlrc` and exposes
`<package>/bin` in both build and run environments, so consumers such as djstub can
use the compiler without a cache path compiled into the executable.

Upstream provides no automated Make test target. The consumer test therefore:

1. checks all packaged commands and the transitive NASM command;
2. checks the packaged headers and standard library;
3. generates Linux/x86 assembly without invoking NASM; and
4. builds a DOS executable through the full preprocessor/compiler/NASM/linker flow
   and checks its `MZ` signature without attempting to run it on OHOS.

## Dependencies and W0 decision

- Required runtime tool: NASM 2.16.03.
- W0 was initially blocked because `nasm/2.16.03` had no published Conan recipe.
- NASM was adapted separately in PR #5115 and is now merged and published in the
  `ohpcd` remote for OHOS/armv8.
- Official Smallerc CI #21296 resolved and downloaded the published NASM package,
  confirming that the dependency closure is available without local recipes.

No NASM implementation is included in issue 2049. The Smallerc recipe keeps the
runtime dependency explicit as `nasm/2.16.03`.

For the initial device validation, the immutable Smallerc input archive was augmented
with the NASM recipe from that separate clean worktree. This made the dependency
available to an isolated Conan home without adding NASM files to the Smallerc branch.
That initial input archive SHA256 was
`db9a8da888b27ba21dda21366cdd8ef94c9599e68e4fd3aa108f58d295c232e1`.
The final fix validation used the published NASM package directly from `ohpcd`.

## Validation status

- Official commit and source SHA256: verified locally; `conan source` also
  downloaded, verified, and unpacked the archive successfully.
- Makefile, path discovery, target libraries, and upstream tests: inspected.
- Python and YAML parsing, Bash syntax, `conan inspect`, and `conan export`: passed
  locally with Conan 2.29.1.
- Linux-native dependency graph: parsed the Smallerc recipe and stopped only at
  the unresolved `nasm/2.16.03` reference, as expected.
- OHOS dependency graph: not runnable with the local standard Conan build because
  it does not include this project's private `os=OHOS` setting extension.
- Single-package device Shadow CI: passed on the OHOS/aarch64 device at Smallerc
  fix commit `1d417792a0e4fb169a963bf89512c5f17bdd640e`.
- Conan create summary: total 1, success 1, failed 0, pass rate 100%.
- Gates: L0, L1, L2, L4, and L5 passed. L2 accepted four non-blocking
  version/help warnings because those upstream tools do not implement a conventional
  version/help interface; `smlrpp --version` passed.
- `test_package` discovered all five Smaller C commands and NASM, checked the
  packaged `SMLRC` resources, generated Linux/x86 assembly, produced a DOS
  executable through the preprocessor/compiler/NASM/linker flow, and verified its
  `MZ` signature.
- The destructive negative test passed after the packaged `bin`, `lib`, and
  `include` directories were moved aside, confirming that the test uses package
  artifacts.
- Shadow run directory:
  `/storage/Users/currentUser/ohpc-ci-shadow/runs/1d417792a0e4-20260812T095420Z-run-3167`.
- Immutable input SHA256:
  `3db1f544b0ae368e99babfb20e856b52747038902ab94c9125550a6fdc865e6f`.
- Runner completion: `status=pass`, `setup_rc=0`, and `build_rc=0`.
- Official PR CI #21296 reached the Smallerc build after downloading NASM, then the
  SDK `lld` loaded an incompatible `libxml2.so.16` from the persistent worker's
  `~/usr/local/lib`. The same environment also injected that prefix through
  `CPPFLAGS` and `LDFLAGS`. The recipe now isolates those ambient search variables
  for the Make subprocess and prepends the active compiler SDK's `llvm/lib` to
  `LD_LIBRARY_PATH`, derived from the configured compiler path rather than a fixed
  SDK version.

The repository's software-level L0k check may warn when `commands.json` is absent.
The task constraint permits changes only under this version directory, so no file
was added to the software-level directory.

## Next validation commands

Dependency-remote validation:

```sh
conan download "nasm/2.16.03" -r=ohpcd --only-recipe
CI_PACKAGES="archives/s/smallerc/1.0.2" zsh ci/conan/build_and_test.sh
```

Single-package shadow CI:

```sh
/path/to/run-ohos-shadow-ci.sh archives/s/smallerc/1.0.2
```

Run with an isolated writable directory on the device:

```sh
export RUN_DIR="$HOME/ohos-jobs/smallerc-2049"
export TMPDIR="$RUN_DIR/tmp"
export TMPPREFIX="$RUN_DIR/tmp/zsh"
mkdir -p "$TMPDIR"
CI_PACKAGES="archives/s/smallerc/1.0.2" zsh ci/conan/build_and_test.sh
```

Expected functional evidence includes discovery of all five Smaller C commands and
NASM, a non-empty generated assembly file, a non-empty DOS executable, and the `MZ`
signature check.
