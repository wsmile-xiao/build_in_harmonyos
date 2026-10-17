# rpg 1.2.0 adaptation notes

## Build environment

- Date: 2026-07-30
- Package type: pure Python command-line application
- Native Conan validation: Conan 2.30.0, Linux x86_64
- Cross-package validation: OHPCD Conan 2.29.1, OHOS 6.0 armv8
- Emulator validation: HarmonyOS PC emulator reachable over hdc, no Python 3
  runtime available in the emulator image
- Status: built, not published

## Adaptation

The recipe downloads the exact PyPI 1.2.0 source release and verifies its
SHA-256 digest. It runs the complete upstream pytest suite in an isolated build
environment, packages the `rpg` modules, and generates a relocatable `bin/rpg`
entry point. No upstream source patch is applied.

The entry point inserts the package-relative `lib/python` directory before
calling `rpg.RapidPeptidesGenerator.main()`. This preserves the public command
name in `--version` output and avoids an installation-time absolute path.

## Dependencies

- Runtime: Python 3
- Upstream test runner: pytest 7.4.4
- Native target dependencies: none

## Verification completed

Native `conan create`:

```text
Upstream inventory: 40 pytest cases
Executed: 40
Passed: 40
Failed: 0
Skipped: 0
Pass rate: 40/40 (100%)

Added consumer tests: 3
Executed: 3
Passed: 3
Pass rate: 3/3 (100%)
```

Repository CI script `ci/conan/build_and_test.sh` was also executed for
`archives/r/rpg/1.2.0`:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: rpg --version OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Build Summary: Total 1, Success 1, Failed 0
```

The consumer tests execute the packaged command and verify:

1. Exact `rpg --version` output.
2. Deterministic Arg-C digestion of `DRVYIHPFHL`.
3. A nonzero failure and diagnostic for an invalid enzyme identifier.

The OHOS 6.0 armv8 Conan run completed the same 40 upstream cases and produced
the target package. Runtime execution is kept separate from this cross-package
result because `conan.tools.build.can_run()` does not run the Linux Python
consumer script for the OHOS host profile.

## Runtime note

The target must provide Python 3. On first import, upstream code creates
`rpg_user.py` under the user's `HOME`; consumer tests use a temporary HOME and
clean it up automatically. The connected HarmonyOS PC emulator was reachable
through `hdc` and reported `x86_64`, but did not provide `python` or `python3`,
so no emulator runtime claim is made.
