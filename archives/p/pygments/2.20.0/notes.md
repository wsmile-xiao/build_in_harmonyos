# Pygments 2.20.0 adaptation notes

## Build environment

- Build system: custom pure-Python packaging
- Build date: 2026-08-06
- Compiler: N/A (pure Python package)
- Status: published

## Source audit

- Upstream project: https://github.com/pygments/pygments
- Release: `2.20.0`
- Source archive: official PyPI sdist
- Source SHA256: `6757cd03768053ff99f3039c1a36d6c0aa0b263438fcab17520b30a303a82b5f`
- Python requirement from upstream metadata: Python 3.9 or newer.
- The sdist contains the upstream pytest test suite under `tests/`.

## Packaging

1. Download and verify the official PyPI source archive
   (`https://files.pythonhosted.org/packages/c3/b2/.../pygments-2.20.0.tar.gz`).
2. Apply declared Conan patches. This version has no patches.
3. Run the upstream core API tests with
   `PYTHONPATH=<source> python -m pytest -q tests/test_basic_api.py
   tests/test_cmdline.py tests/test_using_api.py tests/test_token.py`.
4. Copy the whole `pygments/` package tree into
   `lib/python/site-packages/pygments` (keep_path=True, src=pygments/).
5. Copy the BSD-2-Clause LICENSE into the package.
6. Expose the package via `PYTHONPATH` in `package_info()`.
7. Run the consumer test against the packaged module through Conan's run
   environment.

## Test evidence

- Local upstream source runner (OHOS 6.0 armv8 host profile):
  - Core API tests: `2469 passed, 8 skipped`.
- `conan create`:
  - `package(): Packaged 339 '.py' files`.
  - `test_package` consumer test passed (`pygments 2.20.0 ok`).
- Conan verify gates:
  - G0 pre-build assessment: PASS
  - G1 recipe completeness: PASS
  - G2 conan create (clean build): PASS
  - G3 system-lib collision isolation (R26): PASS (no system-named libs)
  - G4 artifact integrity: PASS
  - L2 platform smoke test: PASS
  - L4 static security scan: PASS (no ELF binaries, pure Python)
  - L5 product baseline comparison: PASS

## Dependencies

- Runtime dependencies: Python 3.9 or newer.
- Conan package dependencies: none.
- Optional dependency not enabled: colorama (only needed for
  Windows-terminal extra).

## 结束标记

最终状态: published
