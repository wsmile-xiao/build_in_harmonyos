# mdurl 0.1.2 adaptation notes

## Build environment

- Build system: custom pure-Python packaging
- Build date: 2026-07-27
- Compiler: N/A
- Status: built

## Source audit

- Upstream repository: https://github.com/executablebooks/mdurl
- Tag: `0.1.2`
- Tag commit: `596bf1c8752de45fa576a52c315d6d8cc5bb1a4e`
- Source SHA256: `99d4fabddab7ee4a05fa458deb1a6f0d009966e4631c50d1b875767a1cd3896d`
- The PyPI sdist does not contain the upstream `tests/` directory. The recipe
  therefore uses the official GitHub tag archive.

## Packaging

1. Download and verify the official tag archive.
2. Apply declared Conan patches. This version has no patches.
3. Install pytest into the isolated Conan build folder.
4. Run all upstream pytest cases against `src/mdurl`.
5. Copy the pure Python module and `py.typed` marker into
   `lib/python/site-packages/mdurl`.
6. Copy the MIT license into the package.
7. Run the consumer test against the packaged module through Conan's run
   environment.

## Test evidence

- Windows native Conan 2.29.1 / Python 3.11.9:
  - Upstream suite: `188/188` passed.
  - Packaged consumer suite: `20/20` assertions passed.
- Clean Linux container / Conan 2.29.1 / Python 3.12.13:
  - Upstream suite: `188/188` passed.
  - Packaged consumer suite: `20/20` assertions passed.
- OHOS 6.0 armv8 host profile:
  - Source verification, upstream `188/188` tests, and packaging passed.
  - The consumer test was not run in the Windows cross-profile invocation.
- Network access is required only to download the source archive and pytest.
  The tests themselves are offline and deterministic.
- HarmonyOS PC device execution: not run.
- Competition CI: not run yet.

## Dependencies

- Runtime dependencies: Python 3.7 or newer.
- Conan package dependencies: none.
- Build-only test dependency: pytest 9.1.1.
