# coin-utils 2.11.13 OpenHarmony Port Notes

## Scope

This package ports COIN-OR CoinUtils 2.11.13 to the OpenHarmony PC
aarch64 target. CoinUtils provides sparse matrix, MPS parsing, factorization,
and helper data structures used by downstream COIN-OR packages such as
coin-osi, coin-clp, and coin-cbc.

## Issue/PR split

- Related downstream PR: #3877 for coin-osi 0.108.12.
- Current branch: `feat/coin-utils-2.11.13`.
- Recipe scope: `archives/c/coin-utils/2.11.13/**`.

## Dependency graph

```text
coin-utils/2.11.13
  |-- bzip2/1.0.8
  `-- zlib/[>=1.2.11 <2]
```

BLAS, LAPACK, Glpk, and ASL are optional upstream features and are disabled
with `--without-*` configure arguments for this OpenHarmony package.

## Validation plan

1. Run local static checks:
   `python -m py_compile conanfile.py test_package/conanfile.py`
   and `git diff --check`.
2. Run OHPCD CI L0-L2 with `conan create` and the consumer `test_package`.
3. After #3877 is updated to depend on `coin-utils/2.11.13`, run downstream
   integration validation with coin-osi.

## Validation result

Local static checks passed in this update:

- `python -m py_compile archives/c/coin-utils/2.11.13/conanfile.py archives/c/coin-utils/2.11.13/test_package/conanfile.py`
- `git diff --check`

Full OpenHarmony target validation passed on a physical OpenHarmony PC using:

```text
conan create archives/c/coin-utils/2.11.13 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=coin-utils/*
```

The run built and installed `libCoinUtils.a`, created the Conan package,
compiled and signed `coinutils_smoke`, and executed it successfully on target.
The package metadata explicitly exports both `include` and `include/coin`;
downstream integration was validated by building and running the PR #3877
coin-osi consumer test on the same target.

The metadata intentionally keeps this version as `draft` until repository CI
completes, following the merged #3519 status convention.
