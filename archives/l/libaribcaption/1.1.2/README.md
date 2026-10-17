# libaribcaption 1.1.2 for HarmonyOS

Portably decode and render ARIB STD-B24 subtitles (Japanese ISDB
broadcast captions) with C and C++ APIs. This recipe is the OpenHarmony
PC (aarch64, musl) adaptation of libaribcaption 1.1.2.

- Upstream: <https://github.com/xqq/libaribcaption>
- License: MIT

## Build

```sh
conan create . --build=missing -pr:h=ohos-aarch64 -pr:b=default
```

The upstream CMake falls into its generic Unix branch on OHOS, so the
renderer backend (fontconfig + freetype) is enabled, matching upstream
Linux builds. Both dependencies are W0-published packages.

Options:

| option | default | description |
|---|---|---|
| `shared` | `False` | shared (`libaribcaption.so`) or static library |
| `with_renderer` | `True` | renderer backend (fontconfig + freetype) |

## Notes for OHOS

- Upstream sets no `SOVERSION`, so `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`
  is re-armed with the standard `-Wl,-soname,` prefix at configure time;
  CMake appends the target name and the shared library carries
  `DT_SONAME=libaribcaption.so` (relative), which is also its installed
  file name.
- Upstream's `find_package(Freetype/Fontconfig)` (CMake bundled modules)
  cannot see packages under the conan cross root; small patches switch
  these calls to the CMakeDeps config packages (`freetype::freetype`,
  `fontconfig::fontconfig`) — see `patches/`.
- The upstream test suite (8 targets) is `EXCLUDE_FROM_ALL` and has no
  ctest registration; the 5 self-contained tests are built and run in
  the recipe `build()`. `caption2srt`/`ffmpeg` tests need an external
  MPEG-TS sample that upstream does not ship.

## Test

```sh
conan create . --build=missing -pr:h=ohos-aarch64 -pr:b=default
# test_package (C API + C++ API consumers) runs automatically at the end.

# harmonyos-test (device checks: aarch64, musl, SONAME, NEEDED,
# .codesign, real decode):
harmonyos-test/run.sh <package_prefix> <conan_toolchain.cmake>
```

## Files

| file | description |
|---|---|
| `conanfile.py` | recipe (build, upstream tests, package) |
| `conandata.yml` | source URL + SHA256 |
| `patches/` | find_package → CMakeDeps config switch |
| `test_package/` | C API + C++ API consumers |
| `harmonyos-test/` | HarmonyOS-specific runtime & ELF checks |
