# DRAFT: eigenpy test_package loader fallback on OHOS

> Status: Draft | Updated: 2026-08-29
> Source event: `eigenpy/3.13.0` HarmonyOS PC adaptation after Boost.Python dependency merge

## Summary

`eigenpy`'s consumer test should try the real Python import path first. On OHOS,
the packaged `libeigenpy.so` depends on `libpython3.12.so.1.0`, so the test
runner must add the device Python library directory to `LD_LIBRARY_PATH` before
executing the C++ smoke test or importing the Python extension. After that, an
import can still be blocked by loader policy even when the installed extension
is a valid ELF object. In that case, the test should fall back to static ELF
inspection and record the platform limitation.

## Symptoms

- `python3 test_import.py` fails when importing `eigenpy`.
- `test_version` fails with `Error loading shared library
  libpython3.12.so.1.0` or unresolved Python symbols even though package build
  and install succeeded.
- The CI worker Python raises `ModuleNotFoundError: No module named 'numpy'`
  even though the package was built with pinned NumPy C headers.
- The installed `eigenpy_pywrap` extension exists and is a valid ELF file.
- `llvm-readelf -d` still shows sane `NEEDED` entries.

## Adaptation Pattern

- Sign the consumer executable before running it on OHOS.
- Locate the active interpreter's `LIBDIR`/`LIBPL` and prepend the resolved
  Python library directory to `LD_LIBRARY_PATH` alongside dependency libdirs.
- Run the Python import smoke test first.
- If import is blocked by loader policy, inspect the installed extension with
  `llvm-readelf -d` and treat the result as a platform limitation.
- If the OHOS worker lacks runtime NumPy, use the same static inspection
  fallback after the C++ consumer link/API smoke test succeeds.

## Validation

- `python3 test_import.py`
- `LD_LIBRARY_PATH=<package-libdirs>:<python-libdir> ./test_version`
- `llvm-readelf -d <installed eigenpy_pywrap>`
- verify the test package still installs and exposes `PYTHONPATH`

## Do Not

- Do not replace import coverage with static inspection when import works.
- Do not assume package dependency libdirs include the interpreter's own
  `libpython` directory.
- Do not require runtime NumPy on an official worker that only needs to prove
  the package's native artifacts were built and linked correctly.
- Do not mark a valid loader-policy block as a source build failure.
