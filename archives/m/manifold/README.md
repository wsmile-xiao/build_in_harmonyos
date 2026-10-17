# manifold

Manifold 是一个专注于拓扑鲁棒性的 C++ 三维几何库，用于创建和操作「流形三角网格」（manifold triangle meshes），保证布尔运算等操作的数值稳定与拓扑正确。

## 功能概述

- **网格布尔运算**：Union / Difference / Intersection 等布尔操作，保证输出拓扑流形（manifold）
- **CrossSection（2D）**：二维多边形裁剪与偏置（基于 Clipper2），支持 2D/3D 互转
- **SDF 建模**：从符号距离场（SDF）构造网格
- **凸包 / 平滑 / 属性插值 / 网格修复** 等几何处理能力
- **C FFI 绑定（manifoldc）**：提供 C 接口，便于其他语言/API 集成
- 纯 C++17 实现，附带丰富 GTest 测试套件（经 ctest 注册）

## OHOS 适配

- **构建系统**：cmake（C++17）。已在 HarmonyOS aarch64 环境验证。
- **依赖注入**：上游默认通过 FetchContent git clone 拉取 GTest / Clipper2，但 OHOS 真机无法从 GitHub git clone，因此配方关闭 `MANIFOLD_DOWNLOADS`，改由 Conan 提供 `gtest/1.17.0.2` 与 `clipper2/2.0.1`（并通过 `find_package` 命中）。
- **可选特性**：`MANIFOLD_PAR`（TBB 并行）、`MANIFOLD_PYBIND`（Python/nanobind）、TRACY、ASSIMP、FUZZ 在 OHOS 上全部关闭，只构建核心库 + CrossSection + C 绑定 + 测试。
- **上游测试**：`MANIFOLD_TEST=ON`，`gtest_discover_tests` 将 GTest 用例注册为 ctest 条目，在配方 `build()` 内通过 ctest 完整执行并产出 `HMBS_UPSTREAM_TEST_RESULT` 证据。

## 依赖关系

- **编译/运行依赖**：无第三方运行时依赖；CrossSection 编译期链接 Clipper2（PRIVATE，pimpl 隔离，公共头不暴露 Clipper2）
- **测试依赖**：gtest/1.17.0.2（仅构建/测试期）
- **构建工具**：cmake、C++17 编译器（clang）

## 参考资料

- 官网/文档：https://manifoldcad.org
- 源码仓库：https://github.com/elalish/manifold
- 许可证：Apache-2.0
