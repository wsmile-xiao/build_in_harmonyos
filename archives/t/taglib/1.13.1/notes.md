# taglib 1.13.1 adaptation notes

## Why 1.13.1 alongside 2.3

taglib 2.3 is already archived with `BUILD_BINDINGS=False`. Downstream
consumers that use the official C API (ezstream links `tag_c.h` /
`libtag_c`) need the 1.13.x line because its C bindings ABI is the one
shipped by distributions for the stable C interface. The two versions do
not conflict: they are separate conan references (`taglib/1.13.1` vs
`taglib/2.3`).

## Source verification

- Source URL: `https://github.com/taglib/taglib/releases/download/v1.13.1/taglib-1.13.1.tar.gz`
- SHA256: `c8da2b10f1bfec2cd7dbfcd33f4a2338db0765d851a50583d410bacf055cfd0b`
- Verified on: 2026-09-04 (downloaded and rebuilt from the official asset)

The 1.13.1 release tarball vendors utf8cpp directly as headers under
`3rdparty/utf8-cpp/` (checked.h, core.h). `taglib/CMakeLists.txt` adds
`${taglib_SOURCE_DIR}/3rdparty` to the include path, so the build is
self-contained: no Conan utf8cpp dependency and no network download.

## Build configuration

- Build system: CMake (upstream `cmake_minimum_required(VERSION 3.0.0)`)
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` is required because CMake 4.x removed
  compatibility with `< 3.5`; without it configuration fails immediately
  at CMakeLists.txt:1. Verified with a bare local configure with cmake
  4.1.2 before writing the recipe. **It must be set through
  `tc.cache_variables`** (a `-D` on the cmake command line), not
  `tc.variables`: toolchain `set()` lines are parsed after
  `cmake_minimum_required()` and arrive too late.
- `BUILD_BINDINGS=ON` (the 1.13.x default) keeps `bindings/c` in the build:
  `libtag_c.a` + `include/taglib/tag_c.h` + `taglib_c.pc` are installed.
- `BUILD_SHARED_LIBS=OFF` (static, per repository default for libraries),
  `TAGLIB_STATIC` is defined for static consumers.
- `WITH_ZLIB=ON`: Conan zlib is mapped onto the `ZLIB::ZLIB` CMake target
  via CMakeDeps `set_property` (same approach as the 2.3 archive), because
  upstream uses `find_package(ZLIB)` in module mode.
- `CMAKE_FIND_PACKAGE_PREFER_CONFIG=True` is required so the CMakeDeps
  configs actually define the imported targets the upstream link lines
  use (`CppUnit::cppunit` in tests/CMakeLists.txt:76). With module-mode
  find the config is found (message "Found cppunit: CppUnit::cppunit")
  but no imported target exists and generation fails.
- The upstream `FindCppUnit.cmake` only sets `CPPUNIT_INSTALLED_VERSION`
  when a `cppunit-config` program exists. With Conan-provided cppunit it
  does not, so `macro_ensure_version()` is invoked with an empty version
  argument and aborts ("Macro invoked with incorrect arguments"). The
  recipe injects `CPPUNIT_INSTALLED_VERSION=1.15.1` to satisfy the
  1.14.0 minimum-version check.
- The C bindings library links against `tag` (tag_c.cpp wraps the C++
  API), and carries the C++ runtime dependency implicitly. Pure C
  consumers link with `-lc++` (verified locally); CMake consumers get it
  from the `taglib::tag_c` interface (`tag_c.system_libs = ["c++"]`,
  mirroring upstream's explicit Solaris Crun handling).
- `cpp_info.components` is used ("tag" + "tag_c"). With components the
  zlib requirement must be surfaced on the tag component itself
  (`tag.requires = ["zlib::zlib"]`) — package-level requires are not
  inherited by components and test_package linking fails with
  undefined `inflate*` otherwise.

## Upstream tests

- `BUILD_TESTING=ON` compiles the CppUnit `test_runner`: 38 test files,
  364 `CPPUNIT_TEST` cases. CppUnit is discovered through the upstream
  `FindCppUnit.cmake` module; the recipe injects the Conan cppunit
  include dirs and the `CppUnit::cppunit` target into the classic
  `CPPUNIT_*` variables so the module check succeeds.
- On OHOS the aggregate `test_runner` is compiled but not executed in
  recipe `build()` — the same CI-runtime segfault policy recorded for
  taglib 2.3 (CI #11530). Linux builds still run it through CTest when
  runnable.
- `bindings/c/tag_c.cpp` itself is compiled into `libtag_c` during the
  build (target `tag_c`), which is the C bindings' own implementation
  coverage.

## Consumer test (R34)

`test_package/test_tag_c.c` is a pure-C program that includes
`<taglib/tag_c.h>` and links `taglib::tag_c` — the exact consumption
pattern of ezstream. It:

1. writes a minimal canonical WAV file (44-byte header + 4 samples),
2. opens it with `taglib_file_new`, checks `taglib_file_is_valid`,
3. reads empty tag state, sets title/artist/genre/year/track,
4. checks audio properties (sample rate 8000, channels 1),
5. saves with `taglib_file_save`, reopens, and verifies the persisted
   title/artist/year/track round-trip.

Locally verified end-to-end with the staged install before packaging:
`title='HarmonyOS' artist='OpenHarmonyPC' rate=8000 ch=1`. The packaged
test links through `taglib::tag_c`; because the source is plain C but the
library carries C++, the test executable drives the link with
`LINKER_LANGUAGE CXX` and inlines `LD_LIBRARY_PATH` pointing at the OHOS
native toolchain's `libc++_shared.so` (conanrun env lists do not
reliably propagate on OHOS).

## Current status

Recipe, source verification (sha256), consumer test, and MANIFEST are
complete. No patches required: the 1.13.1 official tarball builds cleanly
with clang 15.0.4 targeting aarch64-linux-ohos (one upstream warning in
tlist.tcc, no errors).
---

**编译结束**: 2026-09-04 17:33
**最终状态**: built
