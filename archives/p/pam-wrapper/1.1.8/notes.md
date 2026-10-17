# pam-wrapper 1.1.8 adaptation notes

## Scope

- Issue: 1763
- Worktree: `D:\harmonyos\worktrees\pam-wrapper-pr4234`
- Branch: `feat/pam-wrapper-1.1.8`
- Allowed edit scope: `archives/p/pam-wrapper/1.1.8/` and the two
  pam-wrapper knowledge drafts under `knowledge/graph/draft/`

## W0 dependency check

`pam-wrapper` is a CMake cwrap project for testing PAM applications and PAM
modules. It builds:

- `libpam_wrapper.so`, an LD_PRELOAD interposition library
- `libpamtest.so`, the public C helper API
- PAM test modules such as `pam_matrix.so`
- optional Python bindings when Python development headers are present

The hard dependency is a PAM implementation. Source inspection shows direct
use of `security/pam_appl.h`, `security/pam_modules.h`, `security/pam_ext.h`,
`libpam`, and optionally `pam_misc`. No `linux-pam`, `openpam`, or equivalent
Conan recipe was found under `origin/main` in this repository.

The upstream CTest suite also requires `cmocka >= 1.1.0`. Conan 2.29.1
successfully downloaded the `cmocka/2.0.2` and `linux-pam/1.7.2` recipes from
the `ohpcd` remote. The default dependency graph resolves cmocka as a
non-visible test requirement, and `conan install --build=never` resolved both
OHOS dependency binaries.

## Source and build analysis

- Source URL: `https://ftp.samba.org/pub/cwrap/pam_wrapper-1.1.8.tar.gz`
- SHA256: `6549c0b3e41d1ebe0c94a1be63c25eec918191462b602ab6f47d4a5fa709c3e4`
- Build system: CMake, top-level `CMakeLists.txt`, minimum CMake 3.20
- Default recipe mode: `with_upstream_tests=True`, `UNIT_TESTING=ON`
- Opt-out mode for non-runnable cross-builds: `with_upstream_tests=False`

Upstream always adds `src/python`; the Python extension target is only built
when CMake finds Python 3.10 development files, so no patch is needed for the
default C/C++ package path.

## Prepared Conan package

The recipe and test package are prepared against the separately adapted
`linux-pam/1.7.2` package.

The consumer test is not an empty smoke test. It:

- builds a C program against `libpamtest.h`
- loads `libpam_wrapper.so` with `dlopen`
- uses a pre-created PAM service file pointing at installed `pam_matrix.so`
- uses a small passdb created before the test process starts
- runs `run_pamtest()` and verifies a successful authentication result

`test_package/test_pam_wrapper.c` was rechecked against the official
`pam_wrapper-1.1.8` sources. In the non-DOXYGEN build path,
`run_pamtest()` is a macro that passes `sizeof(test_cases) /
sizeof(test_cases[0])` to `_pamtest()`, and `src/libpamtest.c` iterates
with `tcindex < num_test_cases`. The single-entry `tests[]` array is
therefore bounded by an explicit count rather than a sentinel.

## Local verification

Performed locally:

- Downloaded the official tarball
- Computed SHA256
- Inspected CMake dependency detection and upstream tests
- Confirmed the default Conan graph and OHOS dependency binaries
- Regenerated four per-file portability patches through
  `ohc-run.py refresh-patch --auto`; all passed `patch --dry-run -p1`
- Parsed recipe Python files and checked the archive diff for whitespace errors

Not performed locally:

- Upstream CTest execution: the Windows host cannot execute OHOS binaries

## OHOS real-device verification

Device run: `/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-pam-wrapper-pam-wrapper-1.1.8-r3-conan5-20260806-132958-13395`

Command shape:

```sh
sh "$HOME/bin/ohos-test-runner.sh" --try-lock \
  --user codex-pam-wrapper \
  --lib pam-wrapper \
  --task pam-wrapper-1.1.8-r3-conan5 \
  --mode heavy \
  --workdir /storage/Users/currentUser/ohos-users/codex-pam-wrapper/pam-wrapper-1.1.8-r3/repo/build_in_harmonyos \
  --path "$HOME/.local/bin:$HOME/usr/local/bin:/data/service/hnp/bin" \
  -- sh /storage/Users/currentUser/ohos-users/codex-pam-wrapper/pam-wrapper-1.1.8-r3/run-pam-wrapper-ci.sh
```

Result:

- L0: pass
- L1: pass, `test_package` executed and printed `pam-wrapper libpamtest authentication check passed`
- L2: skip, no `bin/` directory for this library package
- L4: pass, patch scan clean
- L5: pass, library artifacts present

Portability fixes found during device validation:

- Upstream CMake detection needed Conan-provided PAM include/library paths
  instead of system `pam`/`pam_misc` names.
- OHOS package artifacts need `.so` signing before runtime loading; signing
  tools are resolved from environment/PATH and missing tools fail the package
  step instead of silently skipping signing.
- `pam_wrapper` copies `PAM_WRAPPER_SERVICE_DIR` during `LD_PRELOAD`
  initialization, before `main()`, so the test service/passdb files must be
  created by the Conan test recipe before launching the executable.

## Upstream CTest validation

The default recipe now builds and runs upstream `test_pam_wrapper`, which
contains 23 CMocka cases. CMocka is a test requirement rather than a runtime
dependency. Before CTest on OHOS, the recipe signs the built test executable,
`pam_wrapper`/`pamtest`, and test PAM modules. A private writable `TMPDIR` is
used for the suite, and CTest prints its inventory and full verbose output.

Actual execution completed on the aarch64 OHOS 6.0 device. The default
`conan create` command used `with_upstream_tests=True` without an option
override, resolved `cmocka/2.0.2` as `test=True, visible=False`, signed the
build-tree ELF files, and ran the registered `test_pam_wrapper` CTest target.
All 23 CMocka cases passed, followed by successful packaging and the consumer
`test_package` authentication check.

- Run: `/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-upstream-20260807-144624`
- Package: `pam-wrapper/1.1.8#2f2f502a01f65d32961ddcb33f306d87:e1f2846c4ee5b18d6bc5c6d0966b2fee34777e5a#cc0baa281cc9b34bad9fab1da9e674b9`
- CTest result: 1/1 target passed, 23/23 CMocka cases passed
- Log: `upstream-ctest.log`, SHA256
  `9660199e69663db0bcced0d4bf802d3d6e318219030ecad4e731bd7806c9ed87`
- Repository CI: L0/L1/L4/L5 pass; L2 skipped because this library has no
  `bin/` directory
- Repository CI log: `repo/.ci_logs/conan_build_pam-wrapper_1.1.8.log`,
  SHA256 `a181e7753188788ad47bd24a4196d2d68e47208a377d4949a9ba3370283d59c7`
- `ohc-run.py conan-verify`: overall pass; G0/G1/G2/G3 passed. Its G4
  package-ID lookup did not resolve the hyphenated package reference, so its
  L2/L4/L5 checks were skipped; the repository CI independently passed L4/L5.
- Conan verify report SHA256:
  `8c5d26bc22cc70ec7371e01ebd55639cb59a7ebc879a87aaf1731294e4b7a50e`

## Knowledge captured

This adaptation adds two draft entries for review rather than changing the
formal graph index directly:

- `DRAFT-pam-wrapper-ctest-elf-runtime-closure` records why package-time ELF
  signing cannot make build-tree CTest binaries, shared libraries, and PAM
  modules executable. It extends E077 from post-install processing to the
  pre-CTest runtime closure without changing E077's existing scope.
- `DRAFT-pam-wrapper-preload-startup-context` records that an `LD_PRELOAD`
  library can copy environment-driven configuration before the consumer's
  `main()` starts. It extends E200's basic LD_PRELOAD verification with the
  parent-setup/child-exec ordering required by stateful interposition tests.

Both drafts cite the same successful OHOS run and CTest log hash above. They
remain drafts so the editor can assign stable E-numbers and merge them with a
newer equivalent entry if one lands first.

Together with E077, E200, and the E223 draft pattern, these entries support a
Path C high-difficulty candidate application. The evidence, counting rules,
and explicit non-claims are in `reports/high-difficulty-evidence.md`; the
ready-to-use PR title and body are in `reports/pr-body.md`. This is an
application for review rather than a claim of an already-approved
classification or score.

## Next steps

Follow-up validation:

1. Confirm the AtomGit PR pipeline uses the default test option.
2. Keep the upstream CTest result visible in the PR description.
