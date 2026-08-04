# sphinxcontrib-qthelp 2.0.0 adaptation notes

## Build environment

- Date: 2026-07-30
- Package type: pure Python Sphinx extension
- Upstream test environment: Python 3.12, Sphinx 9.1.0, pytest 9.1.1
- Native Conan validation: Conan 2.30.0, Linux x86_64 Release and Debug
- Cross-package validation: OHPCD Conan 2.29.1, OHOS 6.0 armv8
- Emulator validation: HarmonyOS PC emulator reachable over hdc, no Python 3
  runtime available in the emulator image
- Status: built, not published

## Adaptation

The recipe verifies and unpacks the exact PyPI 2.0.0 source release, runs all
upstream tests in an isolated environment, and packages the complete
`sphinxcontrib.qthelp` namespace module. No source patch is applied.

Sphinx is used for tests but is not declared as a Conan target requirement.
Sphinx itself consumes this extension, so declaring the reverse edge would
create a dependency cycle.

## Verification completed

The clean upstream run collected exactly four cases:

```text
Executed: 4
Passed: 4
Failed: 0
Skipped: 0
Pass rate: 4/4 (100%)
```

Six `RemovedInSphinx11Warning` messages were emitted by Sphinx 9.1.0. They are
future deprecation notices and did not skip or fail a test.

The Conan consumer test builds a minimal QtHelp document with the packaged
module, verifies the generated `.qhp` and `.qhcp` files, and supplies a malformed
namespace to verify the extension's normalization behavior.

Repository CI script `ci/conan/build_and_test.sh` was also executed for
`archives/s/sphinxcontrib-qthelp/2.0.0`:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content
Build Summary: Total 1, Success 1, Failed 0
```

The OHOS 6.0 armv8 Conan run completed the same four upstream tests and
produced the target package. Runtime execution is kept separate from this
cross-package result because `conan.tools.build.can_run()` does not run the
Linux Python consumer script for the OHOS host profile.

The connected HarmonyOS PC emulator was reachable through `hdc` and reported
`x86_64`, but did not provide `python` or `python3`, so no emulator runtime
claim is made.
