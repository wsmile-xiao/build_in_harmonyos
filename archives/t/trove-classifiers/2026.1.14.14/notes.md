# trove-classifiers 2026.1.14.14 adaptation notes

## Build environment

- Build system: setuptools / pure-Python packaging
- Build date: 2026-07-27
- Compiler: N/A
- Status: built

## Source audit

- Upstream repository: https://github.com/pypa/trove-classifiers
- Release: `2026.1.14.14`
- PyPI source SHA256: `00492545a1402b09d4858605ba190ea33243d361e2b01c9c296ce06b5c3325f3`
- The official source distribution contains the complete upstream `tests/`
  directory.

## Packaging

1. Download and verify the official PyPI source distribution.
2. Apply declared Conan patches. This version has no patches.
3. Create an isolated Python test environment with `venv --without-pip`.
4. Install pytest into a private target directory with the system pip, copy the
   source module into that directory, and run all upstream pytest cases
   unchanged. This avoids relying on `ensurepip`, which is unavailable in the
   OHOS Python runtime.
5. Copy the pure Python package and `py.typed` marker into
   `lib/python/site-packages/trove_classifiers` while preserving any upstream
   subpackage paths.
6. Install the `trove-classifiers` Python entry point under `bin/`.
7. Run the consumer test through Conan's run environment.

## Test evidence

- Windows native Conan 2.29.1 / Python 3.11.9:
  - Upstream suite: `18/18` passed.
  - Packaged consumer suite: `24/24` assertions passed.
- Clean Linux container / Conan 2.29.1 / Python 3.12:
  - Upstream suite: `18/18` passed.
  - Packaged consumer suite: `24/24` assertions passed.
- OHOS 6.0 armv8 host profile:
  - Source verification, upstream `18/18` tests, and packaging passed.
  - The consumer test was not run in the Windows cross-profile invocation.
- Network access is required only to download the source archive and build-only
  Python test dependencies. The tests themselves are offline and deterministic.
- HarmonyOS PC device execution: not run.
- Competition CI: not run yet.

## Dependencies

- Runtime dependency: Python 3.
- Conan package dependencies: none.
- Build-only test dependency: pytest 9.1.1 and its Python dependencies.
