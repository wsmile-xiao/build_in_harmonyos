# SuperNOVAS 1.7.1

## Source

- URL: https://github.com/Smithsonian/SuperNOVAS/archive/refs/tags/v1.7.1.tar.gz
- SHA256: `9709c24e77e287515a6908ed8cf885b87cdd1758c6d3261be98383f74ab7a1af`

## Build

SuperNOVAS is packaged as static C and C++ libraries with CMake:

```bash
cmake -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON -DBUILD_DOC=OFF -DBUILD_EXAMPLES=OFF -DBUILD_BENCHMARK=OFF -DWITHOUT_CURL=ON -DENABLE_CPP=ON -DENABLE_CALCEPH=OFF -DENABLE_CSPICE=OFF -DENABLE_TESTING_ONLINE=OFF
cmake --build .
cmake --install .
```

The package disables network-related curl support and optional ephemeris plugin dependencies for a small deterministic OHOS build.

## Tests

Upstream CMake registers 37 offline CTest entries when the C++ wrapper is enabled:

- 3 C99 tests under `test/c99`
- 34 C++ tests under `test/cpp`

The Conan recipe builds and registers the complete upstream suite. Official OHOS CI for PR #3834 executed all 37 entries successfully: 37/37 passed (100%). A local Windows cross host cannot execute OHOS target binaries, so the official CI result is the target-platform evidence.

The consumer test package builds and runs two packaged-API consumers:

- `test_supernovas_c`: checks Julian date conversion, calendar conversion, vector conversion, observer construction, and version macros.
- `test_supernovas_cpp`: checks `Time`, `Angle`, `Unit`, and `CalendarDate` C++ wrapper APIs.

Official OHOS CI executed both packaged consumers successfully: 2/2 passed (100%). The combined result is 39/39 tests passed (100%). No upstream test was removed or modified.
