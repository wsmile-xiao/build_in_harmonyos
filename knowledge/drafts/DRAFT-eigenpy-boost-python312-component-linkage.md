# DRAFT: eigenpy Boost.Python component linkage

> Status: Draft | Updated: 2026-08-29
> Source event: `eigenpy/3.13.0` HarmonyOS PC adaptation after Boost.Python dependency merge

## Summary

`eigenpy` links Boost.Python as part of its runtime surface. Its Conan
`package_info()` should expose the exact Boost.Python component, not only the
umbrella Boost package, so downstream CMakeDeps consumers inherit the right
target. On OHOS, also pass complete Python CMake hints because Boost.Python's
generated config runs a nested `find_dependency(Python ...)`.

The merged Boost package exports `python`, `python3`, and `python312`. For
this package, `boost::python312` is the component that matches the resolved
Python 3.12 ABI.

## Symptoms

- Downstream consumers see `Boost::boost`-level linkage but miss the exact
  Boost.Python component.
- CMakeDeps target resolution becomes ambiguous even though the recipe already
  knows which Python ABI it is using.
- The package still fails fast when Boost.Python is missing, but the exported
  metadata is too broad.
- CMake configure fails inside `boost_python312-config.cmake` with missing
  `Python_INCLUDE_DIRS`, `Python_LIBRARIES`, or `Development.Embed` even though
  the recipe found a valid Python executable.

## Adaptation Pattern

Set:

```python
self.cpp_info.requires = ["eigen::eigen", "boost::python312"]
```

Keep the existing early `ConanInvalidConfiguration` guard for the missing
`libboost_python312`, `libboost_python3`, or `libboost_python` case.

When cross-building on OHOS, preload the Python cache variables used by both
the old `FindPythonInterp`/`FindPythonLibs` path and modern `FindPython`:

```python
defs.extend([
    '-DPYTHON_EXECUTABLE="{}"'.format(python["executable"]),
    '-DPYTHON_LIBRARY="{}"'.format(python["library"]),
    '-DPython3_EXECUTABLE="{}"'.format(python["executable"]),
    '-DPython3_INCLUDE_DIRS="{}"'.format(python["include_dir"]),
    '-DPython3_LIBRARY="{}"'.format(python["library"]),
    '-DPython3_LIBRARIES="{}"'.format(python["library"]),
])
```

## Validation

- `conan export` for `eigenpy/3.13.0@ohpcd/stable`
- `conan graph info --format=json`
- confirm the Boost recipe exports `python312`
- device shadow CI reaches CMake configure with
  `Found Python: ... Development Development.Module Development.Embed`
- official CI without runtime NumPy should still reach configure by using the
  pinned NumPy header wheel and configure-only stub

## Do Not

- Do not keep `boost::boost` as the only dependency for a Boost.Python package.
- Do not guess a Boost.Python component name that the resolved Boost recipe
  does not export.
