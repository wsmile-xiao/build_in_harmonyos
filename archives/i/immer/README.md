# immer

immer — persistent and immutable data structures written in C++ (header-only).
提供持久化/不可变数据结构（vector / flex_vector / map / set / table / array 等），
面向交互式与并发程序，支持结构共享与透明更新。

- 官方仓库：https://github.com/arximboldi/immer
- 许可证：Boost Software License 1.0（BSL-1.0）
- 版本：0.9.1（标签 `v0.9.1`，release commit `160f0d7025321e5dc1fc3f0b7742ca7621d43981`）
- 目录结构：`archives/i/immer/{version}/`（conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md）

## 说明

- header-only：CMake INTERFACE target `immer`，无 .a/.so 编译产物。
- 上游 CMake 包导出名 `ImmerConfig`（find_package(Immer)），target 名 `immer`。
- 上游 CMake 选项：`immer_BUILD_TESTS`(ON) / `immer_BUILD_EXAMPLES`(ON) / `immer_BUILD_DOCS`(ON) / `immer_BUILD_EXTRAS`(ON)。
- 注意：上游 `project(immer VERSION 0.9.0)` 版本串仍是 0.9.0，但正式发布标签为 `v0.9.1`（上游未同步 CMake 版本串，属上游小瑕疵，不影响以 v0.9.1 为准）。
