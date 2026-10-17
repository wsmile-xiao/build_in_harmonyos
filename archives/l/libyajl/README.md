# libyajl

[libyajl](https://github.com/lloyd/yajl) — Yet Another JSON Library: a small,
fast, portable C library for parsing and generating JSON, written by Lloyd
Hilaiel. Distributed under the ISC license.

## OHOS adaptation

- Built with the upstream CMakeLists.txt via Conan CMakeToolchain.
- Two portability patches replace the removed `GET_TARGET_PROPERTY(LOCATION)`
  pattern with the `$<TARGET_FILE:target>` generator expression (CMake 4.x).
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` cache variable to satisfy CMake 4.x
  policy checking for the legacy `cmake_minimum_required(2.6)` declaration.
- `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,` set explicitly because
  CMake 4.1.2 ships no Platform/HarmonyOS module; keeps the upstream
  `libyajl.so.2` SONAME/SOVERSION behavior.
- Zero runtime dependencies (pure C, libc only).

## Upstream tests

- `test/parsing`: 58 regression cases driven by the `yajl_test` binary
  (flags from filename prefixes), compared against `.gold` expected outputs.
- `test/api`: 1 API-level executable (`gen-extra-close`).

Both the `yajl_test` binary and the case data are packaged so the L1
test_package replays the upstream harness on target.

## References

- https://github.com/lloyd/yajl
- https://lloyd.github.io/yajl/
