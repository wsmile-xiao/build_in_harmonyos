# PyYAML 6.0.2 adaptation notes

## Build environment

- Build system: custom pure-Python packaging
- Build date: 2026-08-01
- Compiler: N/A
- Status: built

## Source audit

- Upstream project: https://github.com/yaml/pyyaml
- Release: `6.0.2`
- Source archive: PyPI sdist
- Source SHA256: `d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e`
- Python requirement from upstream metadata: Python 3.8 or newer.
- The sdist contains the upstream test suite under `tests/legacy_tests`.

## Packaging

1. Download and verify the official PyPI source archive.
2. Apply declared Conan patches. This version has no patches.
3. Run upstream `tests/legacy_tests/test_all.py` with
   `PYTHONPATH=<source>/lib:<source>/tests/legacy_tests`.
4. Force the pure-Python test scope with `PYYAML_FORCE_LIBYAML=0`.
5. Copy `lib/yaml`, `lib/_yaml`, and `PyYAML.egg-info` into
   `lib/python/site-packages`.
6. Copy the MIT license into the package.
7. Run the consumer test against the packaged module through Conan's run
   environment.

## Test evidence

- Local upstream source runner:
  - Pure-Python suite: `1283/1283` passed.
  - Optional LibYAML extension suite: not run because this package does not
    build `yaml._yaml`.
- OHOS 6.0 armv8 host profile:
  - Source verification, pure-Python upstream `1283/1283` tests, packaging,
    and `test_package` passed.
  - Full package reference:
    `pyyaml/6.0.2#945ede326d62a17c4827815da56bb22e:da39a3ee5e6b4b0d3255bfef95601890afd80709#9138d3195e5c4d7a235a1ebf40e7ec00`.
- HarmonyOS PC device execution:
  - CI runner completed with `L0_RESULT=pass`, `L1_RESULT=pass`,
    `L2_RESULT=skip`, `L4_RESULT=pass`, `L5_RESULT=pass`.
  - Build summary: total 1, success 1, failed 0.
- Competition CI:
  - Not run yet.

## Dependencies

- Runtime dependencies: Python 3.8 or newer.
- Conan package dependencies: none.
- Optional dependency not enabled: LibYAML C extension.
