# DRAFT: eigenpy NumPy header wheel fallback

> Status: Draft | Updated: 2026-08-29
> Source event: `eigenpy/3.13.0` official CI #34221 missing runtime NumPy

## Summary

`eigenpy` needs NumPy C headers during compilation. Some OHOS CI workers provide
CPython headers and libraries but do not have the `numpy` Python module
installed for `/data/service/hnp/bin/python3.12`. In that environment, probing
`numpy.get_include()` directly fails before CMake configure.

## Symptoms

- `conan create` reaches recipe `build()`.
- `_discover_python()` finds Python 3.12 but fails with
  `ModuleNotFoundError: No module named 'numpy'`.
- The failure happens before CMake configure, even though the missing artifact
  is only the NumPy C include directory.

## Adaptation Pattern

Keep real `import numpy` as the first path. If it is unavailable, extract the
generated C headers from a pinned CPython 3.12 aarch64 NumPy wheel and prepend a
tiny configure-only `numpy` stub to `PYTHONPATH` while running CMake. The stub
only implements `get_include()` and `__version__`, which is enough for
jrl-cmakemodules and CMake `FindPython3` NumPy probes.

## Validation

- `conan source` extracts `numpy/_core/include/numpy/arrayobject.h`.
- `conan export` succeeds with the pinned wheel metadata.
- Official CI without runtime NumPy should proceed past recipe Python discovery
  and CMake NumPy detection.

## Do Not

- Do not import binary modules from the manylinux wheel on OHOS.
- Do not package the wheel contents as runtime files.
- Do not skip the real NumPy import path when the target interpreter already has
  NumPy installed.
