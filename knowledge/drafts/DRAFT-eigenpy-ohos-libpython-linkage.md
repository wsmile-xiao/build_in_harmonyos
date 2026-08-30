# DRAFT: eigenpy OHOS libpython linkage

> Status: Draft | Updated: 2026-08-29
> Source event: `eigenpy/3.13.0` device shadow CI undefined Python symbols; official CI #34231 `-lintl`

## Summary

When building `eigenpy` for OHOS with shared libraries, lld requires Python API
symbols to be resolved while linking `libeigenpy.so` and the
`eigenpy_pywrap` extension. Upstream CMake links Boost.Python, but that is not
enough for the OHOS toolchain when the Boost.Python package was itself built
against Python 3.12.

## Symptoms

- CMake configure succeeds and finds `Python ... Development.Embed`.
- `libeigenpy.so` or `eigenpy_pywrap` link fails with undefined symbols such as
  `_Py_Dealloc`, `_Py_NoneStruct`, or `PyLong_FromLong`.
- The link command contains `libboost_python312.so` but no
  `libpython3.12.so`.

## Adaptation Pattern

Discover the selected interpreter's `libpython` path, pass it through a dedicated
`OHOS_PYTHON_LIBRARY` cache variable plus the usual CMake `Python`/`Python3`
hints, and patch the upstream target link blocks on OHOS only. Prefer the
direct library file over `Python::Python`, because some worker Python builds add
`-lintl` to the imported target even when the OHOS link environment has no
searchable `libintl`:

```cmake
if(OHOS_PYTHON_LIBRARY)
  target_link_libraries(<target> PRIVATE "${OHOS_PYTHON_LIBRARY}")
elseif(TARGET Python::Python)
  target_link_libraries(<target> PRIVATE Python::Python)
elseif(TARGET Python3::Python)
  target_link_libraries(<target> PRIVATE Python3::Python)
elseif(Python_LIBRARIES)
  target_link_libraries(<target> PRIVATE ${Python_LIBRARIES})
elseif(Python3_LIBRARIES)
  target_link_libraries(<target> PRIVATE ${Python3_LIBRARIES})
endif()
```

Apply this to both the core `${PROJECT_NAME}` library and the `${PYWRAP}`
extension target.

## Validation

- Device shadow CI should build `lib/libeigenpy.so`.
- Device shadow CI should link `python/eigenpy/eigenpy_pywrap.so`.
- `llvm-readelf -d` should show the expected Python and Boost.Python NEEDED
  entries.
- Official CI must not add an unresolved `-lintl` link item from Python's
  imported target while building `libeigenpy.so`.

## Do Not

- Do not rely on Boost.Python to transitively satisfy Python API symbols under
  OHOS lld.
- Do not patch non-OHOS builds unless the same link failure is reproduced there.
