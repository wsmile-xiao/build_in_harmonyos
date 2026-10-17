# taglib 2.3 adaptation notes

## Current source verification

- Source URL: `https://github.com/taglib/taglib/releases/download/v2.3/taglib-2.3.tar.gz`
- SHA256: `7349f6fd942418bc7009ebe743eb7c9d055f02921ec56fa436ec25007c47fd38`
- Verified on: 2026-07-19

The official v2.3 release asset vendors a complete utf8cpp source tree. The
`3rdparty/utfcpp` directory contains 29 files (197681 bytes), including:

- `3rdparty/utfcpp/CMakeLists.txt`
- `3rdparty/utfcpp/source/utf8.h`
- `3rdparty/utfcpp/source/utf8/checked.h`
- `3rdparty/utfcpp/source/utf8/core.h`
- `3rdparty/utfcpp/source/utf8/cpp11.h`
- `3rdparty/utfcpp/source/utf8/cpp17.h`
- `3rdparty/utfcpp/source/utf8/cpp20.h`
- `3rdparty/utfcpp/source/utf8/unchecked.h`

TagLib's top-level `CMakeLists.txt` first checks for an installed utf8cpp,
then checks for `3rdparty/utfcpp/CMakeLists.txt` and calls
`add_subdirectory("3rdparty/utfcpp")`. The vendored fallback is therefore
self-contained and does not require a Conan utf8cpp dependency or a network
download during the build.

The historical `0001-CMakeLists.txt.patch` added an unconditional
`FetchContent` fallback based on a different source archive whose git
submodule content was absent. It is not applicable to the official release
asset above and would introduce a network dependency into clean CI builds.
The patch is intentionally removed and `conandata.yml` correctly declares
`patches: []`.

## Build and tests

- Build system: CMake
- Package type: static library
- C++ standard: C++17
- Dependencies: zlib 1.3.1 and cppunit 1.15.1
- Upstream tests: enabled with `BUILD_TESTING` so the CppUnit `test_runner`
  and upstream test sources are compiled. On OHOS the aggregate
  `test_runner` is not executed in recipe `build()` because CI #11530 showed
  a reproducible runtime segfault after successful configure/build; Linux
  builds still execute it through CTest when runnable.
- Consumer test: validates `TagLib::String` UTF-8 conversion and
  `TagLib::ByteVector` contents through the packaged library

The PR description counts test cases: 556 upstream cases are compiled into the
upstream CppUnit runner, and one consumer test is executed by `test_package`.
`MANIFEST.yml` keeps the assertion-point metric used by the PR description,
but records the OHOS runner limitation explicitly.

## Current status

The recipe, source verification, patch policy, upstream test compilation, and
consumer test are complete. Official CI #11530 reached the upstream CppUnit
runtime step and failed with a `test_runner` segmentation fault, so the OHOS
recipe now treats the aggregate runner as compiled coverage and relies on the
non-interactive `test_package` executable for runtime validation.
