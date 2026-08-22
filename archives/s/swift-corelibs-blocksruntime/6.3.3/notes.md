# swift-corelibs-blocksruntime 6.3.3 Adaptation Notes

## Build Environment

- Platform: HarmonyOS PC arm64 (`os=OHOS`, `arch=armv8`)
- Build system: CMake
- Compiler: Clang 15.0.4
- Conan: 2.29.1
- Build date: 2026-08-20
- Status: built

## Build Steps

The recipe downloads the official `swift-6.3.3-RELEASE` source archive, configures CMake with `BUILD_SHARED_LIBS=ON` and position-independent code, builds the two upstream C sources, installs the shared library, headers, module map, and CMake package metadata, then runs the consumer test package.

## Issues and Solutions

| # | Issue | Root cause | Solution |
|---|---|---|---|
| 1 | Conan recipe import failed | The repository Conan version does not expose `cmake_layout` from `conan.tools.layout` | Use the compatible `basic_layout` helper |
| 2 | Consumer could not find `Block.h` | Upstream installs headers below `include/BlocksRuntime` | Set `cpp_info.includedirs` to `include/BlocksRuntime` |
| 3 | W3 pre-download cache filename was truncated | The CI pre-download URL parser treats hyphens specially | Use the codeload URL with percent-encoded hyphens and provide the expected local cache alias during local validation |
| 4 | Upstream has no test target | The official repository contains only the runtime sources | Add a real `-fblocks` consumer test covering copy, invocation, and release |

## Source Modifications

No upstream source patches were required.

## Dependencies

No Conan dependencies.

## Verification

```text
conan create: PASS
conan-verify: PASS
W3 local CI simulation: PASS
consumer output: BlocksRuntime copy, invoke, and release: OK
```

## Notes

The package exports the CMake target `BlocksRuntime::BlocksRuntime` and installs `Block.h`, `Block_private.h`, and `module.modulemap`.

---

**Build complete**: 2026-08-20 21:00
**Final status**: built

## 结束
