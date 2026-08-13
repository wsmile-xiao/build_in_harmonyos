# Pygments 2.20.0 adaptation notes

## Build environment

- Build system: custom pure-Python packaging
- Build date: 2026-07-30
- Compiler: N/A
- Status: built

## Source audit

- Upstream repository: https://github.com/pygments/pygments
- Release: `2.20.0`
- Source distribution: official PyPI sdist
- Source SHA256: `6757cd03768053ff99f3039c1a36d6c0aa0b263438fcab17520b30a303a82b5f`
- The official sdist contains the complete `tests/` tree.

## Packaging

1. Download and verify the official PyPI source distribution.
2. Apply declared Conan patches. This version has no patches.
3. Install the pinned upstream test dependencies in the Conan build folder.
4. Run the complete upstream pytest suite with a fixed random seed.
5. Copy all pure Python modules into `lib/python/site-packages/pygments`.
6. Install the `pygmentize` entry point under `bin`.
7. Copy the BSD license and author notices into the package.
8. Run the deterministic API and CLI consumer test through Conan's run
   environment.

## Upstream test inventory

- Collected cases: 5224.
- Local source audit: 5208 passed and 16 skipped.
- The skipped cases are upstream explicit skips or require optional external
  tools such as LaTeX and SGML validators.
- Test areas include the public API, command line, lexers, formatters, styles,
  filters, token handling, example files, snippets, and contrast checks.

## Test evidence

- Windows source audit / Python 3.11:
  - Complete upstream suite: `5208/5208` executed cases passed.
  - Upstream skips: 16.
- Packaged consumer suite: 20 deterministic assertions.
- HarmonyOS PC device execution: not run.
- Competition CI: not run yet.

## Dependencies

- Runtime dependencies: Python 3.9 or newer.
- Conan package dependencies: none.
- Build-only test dependencies: pytest 8.4.2, coverage 7.8.0,
  pytest-cov 6.2.1, pytest-randomly 4.1.0, and wcag-contrast-ratio 0.9.
