# cwalk 1.2.9 HarmonyOS PC adaptation

## Upstream

- Repository: https://github.com/likle/cwalk
- Tag: `v1.2.9`
- Commit: `f45a23a13abf39d94b347d7c83810eca26a5a8d0`
- License: MIT
- Language: C11
- Third-party dependencies: none

## Build

The recipe uses the upstream CMake project with a static-library build. It installs
`libcwalk.a`, `cwalk.h`, CMake target metadata, pkg-config metadata and `LICENSE.md`.
No source patch is required.

## Upstream tests

`ENABLE_TESTS=ON` builds the upstream `cwalktest` executable and registers 180
independent CTest cases. The recipe signs that executable once and runs the complete
suite with `ctest --output-on-failure`; no upstream test source or expected result is
modified.

The suite covers absolute and relative paths, basename, dirname, extensions, style
guessing, intersections, joins, normalization, roots, segments, and Windows/Unix path
semantics.

## Consumer test

One Conan consumer executable links the packaged `cwalk::cwalk` target. It verifies
Unix normalization, joining, relative path generation, extension replacement, basename
lookup and Windows path-style handling. Its individual assertions remain part of one
consumer integration-test boundary.
