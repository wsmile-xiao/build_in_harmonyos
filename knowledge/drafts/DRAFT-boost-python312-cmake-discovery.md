# DRAFT: Boost.Python 3.12 CMake discovery on HarmonyOS PC

> Status: Draft | Updated: 2026-08-26
> Source event: `boost/1.90.0.2.1` dependency adaptation for `eigenpy/3.13.0`
> Task hall: `4415`
> PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6712

## Summary

Boost.Python is not just another optional Boost component. The selected CPython
runtime becomes part of the library ABI and the component name that downstream
consumers request. On HarmonyOS PC aarch64, a Boost.Python recipe should pin
CMake `FindPython` to the same OHOS CPython runtime used by the consumer.

For the current eigenpy dependency chain, that runtime is CPython 3.12 and the
Boost package must provide `libboost_python312.so` plus a `Boost::python312`
component.

## Symptoms

Common failure patterns include:

- A downstream package reports that `Boost::python312` cannot be found.
- The Boost package contains `filesystem`, `program_options`, or `system`, but
  no `libboost_python312.so`.
- CMake finds a host Python or an unversioned Python while cross-building.
- Link or runtime logs mention missing `Py_*` symbols or an unexpected
  `libpython` path.

In the eigenpy 3.13.0 precheck, the published `boost/1.90.0.2` package did not
contain a Boost.Python library for Python 3.12. The dependency therefore needed
a new suffix version with Boost.Python enabled.

## Root Cause

Boost's CMake release uses CMake `FindPython`. In a cross-build, leaving
`FindPython` unconstrained can select whichever Python is easiest to discover:
the build host interpreter, an unversioned target interpreter, or headers that do
not match the target shared library.

Boost.Python embeds the selected interpreter ABI in both the library name and the
consumer link interface. If the recipe selects the wrong interpreter, downstream
CMake consumers may configure against misleading metadata or fail to link/run.

## Adaptation Pattern

Query the target runtime interpreter and pass all relevant values as CMake cache
variables:

```python
tc.variables["BOOST_ENABLE_PYTHON"] = True
tc.cache_variables["Python_EXECUTABLE"] = python["executable"]
tc.cache_variables["Python_ROOT_DIR"] = python["prefix"]
tc.cache_variables["Python_INCLUDE_DIR"] = python["include_dir"]
tc.cache_variables["Python_LIBRARY"] = python["library"]
tc.cache_variables["Python_FIND_STRATEGY"] = "LOCATION"
```

The `python` record should come from the interpreter itself, using `sysconfig`
for the include directory, prefix, version, and library hints. If the consumer
chain is pinned to Python 3.12, fail fast when the detected interpreter is not
3.12 instead of silently falling back.

## Package Metadata

After installation, scan the packaged libraries for `boost_python*` and map the
actual ABI-specific library into Conan components:

- `Boost::python`
- `Boost::python3`
- `Boost::python312`

This covers consumers that request generic Boost.Python names and consumers that
request the ABI-specific target.

## Validation

A valid Boost.Python dependency package should prove three things:

1. The package contains the ABI-specific library, such as `libboost_python312.so`.
2. Conan/CMakeDeps exports a component target that downstream consumers can link.
3. A real consumer initializes CPython and exercises Boost.Python symbols at
   runtime.

The `boost/1.90.0.2.1` smoke test links `Boost::python312` and initializes
CPython, then exercises `boost::python::dict` plus
`boost::python::extract<int>()`. On OHOS it links the absolute
`Python_LIBRARY` discovered by the recipe rather than the full `Python::Python`
imported target, because official CI can expose optional system link items such
as `-lintl` without a matching default library search path.

## Do Not

- Do not rely on the build host Python during an OHOS target package build.
- Do not rename or symlink another Boost.Python library to pretend it is Python
  3.12-compatible.
- Do not stop at configure success; perform a real consumer link and runtime
  check.
