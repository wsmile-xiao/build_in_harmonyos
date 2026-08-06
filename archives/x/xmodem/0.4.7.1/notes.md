# xmodem 0.4.7.1 adaptation notes

## Build environment

- Build system: custom pure-Python packaging
- Build date: 2026-08-06
- Compiler: N/A
- Status: built

## Version note

- Conan package version: `0.4.7.1`
- Upstream source version: `0.4.7`
- Reason for suffix: `xmodem/0.4.7` is already published in the artifact
  registry with a different recipe revision. Per CI R37, this recipe update
  uses the incremented Conan package version `0.4.7.1`.

## Source audit

- Upstream repository: https://github.com/tehmaze/xmodem
- Tag: `0.4.7`
- Tag commit: `7c3666fe604fd1144188e484ea86cce74c1d242e`
- Source SHA256: `ed5d0563d6b5bfbeeaceb7a17e07738b7ce60af0e7323ca3e2a6e49942855519`
- Source URL and SHA256 are defined in `conanfile.py` because the CI
  pre-download branch that failed with `BUILD_DIR: parameter not set` runs
  only when `conandata.yml` exists.
- The PyPI sdist omits the upstream `test/` directory. The recipe therefore
  uses the official GitHub tag archive.

## Packaging

1. Download and verify the official tag archive.
2. Install pytest into the isolated Conan build folder.
3. Run all 16 dependency-free upstream protocol tests.
4. When `lrzsz` provides both sender and receiver commands, also run all 8
   upstream external-tool integration tests.
5. Copy the pure Python module into `lib/python/site-packages/xmodem`.
6. Copy the MIT license and protocol documents into the package.
7. Run the deterministic consumer test through Conan's run environment.

## Upstream test inventory

- Unit tests: 16 collected cases, no external dependency.
- Functional tests: 8 collected cases, all require `lrzsz` (`rb`/`lrb` and
  `sb`/`lsb`) and POSIX process I/O.
- Total: 24 collected cases.
- The recipe runs 16/16 unit cases when `lrzsz` is unavailable. It runs all
  24 cases when both external commands are available.

## Test evidence

- 2026-08-06 R37 fix:
  - Package version was incremented from `xmodem/0.4.7` to `xmodem/0.4.7.1`.
  - Source archive remains upstream tag `0.4.7` with the same SHA256.
- 2026-08-06 CI pre-download fix:
  - Moved source URL/SHA256 from `conandata.yml` into `conanfile.py` to avoid
    the CI pre-download `BUILD_DIR` unset path.
  - Verified the SHA256 is unchanged:
    `ed5d0563d6b5bfbeeaceb7a17e07738b7ce60af0e7323ca3e2a6e49942855519`.
- Source audit collection: 24 upstream cases.
- Windows source audit: 16 unit cases collected; the POSIX functional test
  module cannot be collected because the upstream helper invokes `which`.
- Windows native Conan 2.29.1 / Python 3.11:
  - Upstream dependency-free suite: `16/16` passed.
  - Packaged consumer suite: `20/20` assertions passed.
- Clean Linux container / Python 3.12 with lrzsz:
  - Complete upstream suite: `24/24` passed.
- HarmonyOS PC device execution: not run.
- Competition CI: not run yet.

## Dependencies

- Runtime dependencies: Python 3.
- Conan package dependencies: none.
- Build-only test dependency: pytest 8.4.2.
- Optional upstream integration-test dependency: lrzsz.
