# libnu

Small C99 i18n library implementing Unicode 13.0 (UTF-8/16/32, cesu8,
case mapping, collation, normalization helpers).

- Upstream: https://bitbucket.org/alekseyt/nunicode
- License: MIT
- Build: CMake (`nu` static library, headers under `include/libnu`)
- OHOS: pure C99, no extra dependencies; upstream `units` assert suite runs
  in build() via NU_BUILD_TESTS=ON.
