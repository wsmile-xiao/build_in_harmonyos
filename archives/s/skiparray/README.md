# skiparray

`skiparray` is an unrolled skiplist associative array for C, adapted for OpenHarmony PC arm64.

- Version: 0.2.0
- Upstream: https://github.com/silentbicycle/skiparray
- Conan package: `skiparray/0.2.0@ohpcd/stable`

The package exports the static CMake target `skiparray::skiparray`.

The upstream Greatest suite requires `libtheft` 0.4.5. That test-only dependency was not published in the OHOS Conan remote during this adaptation; the core library and a real public-API consumer are packaged, while the incomplete upstream-suite status is reported separately.
