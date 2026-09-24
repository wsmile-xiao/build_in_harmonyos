# liquidfun 1.1.0 adaptation notes

## Build

- Build system: upstream cmake-2.8 tree replaced by patch 0001 (headless top-level CMakeLists)
- Conan package type: library (default static; shared supported)
- Options: `shared=True/False`, `fPIC`
- Dependencies: none — Box2D 2.3.0 is vendored in full; the in-repo box2d/2.4.1 recipe is a different API line and is NOT used
- Patches: `0001-add-headless-cmakelists.patch`
- Platform taskBranch: `feat/liquidfun-1.1.0` (upstream tag v1.1.0 → version 1.1.0)

## Why the upstream build tree was replaced

1. `liquidfun/Box2D/CMakeLists.txt` is cmake-2.8 era and hard-codes `-Wall -Werror` — the 2014 code trips `-Wshift-negative-value` on modern clang (b2ParticleSystem.cpp:55 among others).
2. Line 128 `add_subdirectory(Unittests)` — the real directory is `UnitTests` (case-sensitive breakage on Linux/OHOS; upstream only ever built on case-insensitive/macOS+Windows).
3. `BOX2D_BUILD_EXAMPLES=ON` default drags in freeglut/OpenGL/Testbed — none exist headless.

The replacement CMakeLists globs all 54 sources under `liquidfun/Box2D/Box2D/` (Collision/Common/Dynamics/Particle/Rope) and installs headers preserving the `Box2D/...` relative layout (upstream sources `#include <Box2D/...>` with include root `liquidfun/Box2D`).

## Upstream tests

- 13 gtest binaries registered via `test_executable()` in `liquidfun/Box2D/UnitTests/CMakeLists.txt`: BlockAllocator, BodyContacts, Callback, Color, Common, Confinement, Conservation, FreeList, Function, HelloWorld, IntrusiveList, SlabAllocator, TrackedBlock
- 179 `TEST` macros total (source-counted: 3+8+9+20+3+7+4+11+70+2+23+9+10)
- gtest comes from the vendored `googletest/` sibling at the archive root
- The recipe's build() generates a CMake project that builds the 13 binaries against the vendored gtest + the just-built libliquidfun.a, then runs each through a bash wrapper (OHOS mksh cannot exec cross-built ELF); any non-zero exit fails the build

## Consumer interface

- CMake: `find_package(liquidfun)` / `liquidfun::liquidfun`
- Headers: `#include <Box2D/Box2D.h>` (upstream layout)
- API: Box2D 2.3.0 + b2ParticleSystem (LiquidFun extension)

## Validation

- OHOS aarch64 本机：conan create 全绿（含 13 个上游 gtest 二进制实跑 + test_package 消费者冒烟）
- 详见 PR 正文测试统计表
