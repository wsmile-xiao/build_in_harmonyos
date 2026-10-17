# memory 0.7-4 适配笔记（积分赛任务 #5348）

## 官方来源核验（2026-09-02）

- 官方仓库: https://github.com/foonathan/memory
  （STL-compatible C++ memory allocator library，非 fork）
- 任务版本 0.7-4 对应官方 tag `v0.7-4`
- 官方源码 tarball:
  https://github.com/foonathan/memory/archive/refs/tags/v0.7-4.tar.gz
  - SHA-256: `e6b532c78022709dcf8ae3db9cad0d687df12ec67141f688a01a1abd82ed2810`
  - 大小: 190155 字节
- 许可证: Zlib
- 与已合入 `archives/f/foonathan-memory/0.7/`（同一上游 2022 年 0.7 快照）的关系:
  v0.7-4 为 2025 年上游大改版，本归档独立适配，不共用补丁。

## 与 0.7 版的关键上游差异（实测）

- `CMakeLists.txt` 改用 `$CACHE{...}` 变量语法，`cmake_minimum_required(VERSION 3.14)`。
  实测 CMake 4.1.2 下 `CMAKE_SYSTEM_NAME=HarmonyOS` **不**命中 `if(UNIX)`
  （configure 报「Could not set install folders for this platform!」，知识库 E267 场景），
  仍需平台分支补丁（按 0.7-4 新上下文重写）。
- `container_node_sizes_impl.hpp` 改为 configure 阶段 `try_compile` 解析编译错误文本生成
  （`cmake/get_container_node_sizes.cmake`），**不再需要运行 nodesize_dbg**，
  交叉编译障碍消除；旧 0003 补丁不再需要。
- 不再依赖外部 `debug_assert` 子模块。
- 测试框架从 Catch2 换为 **doctest v2.4.12，经 FetchContent 从 GitHub 下载**——
  离线构建/CI 不可达，已按已交付知识草稿
  `DRAFT-cmake-test-framework-fetch-to-conan-find-package`（PR #7324）的模式
  改为 `find_package(doctest REQUIRED)` + Conan `requires("doctest/2.5.2")`
  （仓库已归档 `archives/d/doctest/2.5.2/`，CMakeDeps 提供 `doctest::doctest`）。

## 补丁（5 个，全部按 v0.7-4 源码生成并用 patch_ng——Conan 的补丁引擎——验证通过）

1. `0001-cmakelists-ohos-platform-branch.patch`（portability，`CMAKE_SYSTEM_NAME` 守卫）
   UNIX 安装目录分支追加 `CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS|OpenHarmony)$"`
   （知识库 E267；CMake 4.x 下 HarmonyOS 不命中 `if(UNIX)`）。
2. `0002-posix-memalign-malloc_allocator.hpp.patch`（portability，`__unix__` 守卫）
   OHOS musl malloc 不保证 max_align 对齐，改用 posix_memalign；零字节请求提升为 1。
3. `0003-posix-memalign-heap_allocator.cpp.patch`（同上）。
4. `0004-posix-memalign-new_allocator.cpp.patch`（同上，按 0.7-4 新上下文重新生成）。
5. `0005-test-find-package-doctest.patch`（conan，FetchContent→find_package）。

## 配方要点

- `name = "memory"` 与任务平台一致；`cmake_file_name/cmake_target_name` 保持
  `foonathan_memory`，供下游（如 type-safe）`find_package(foonathan_memory)` 使用。
- `requires("doctest/2.5.2")` 仅为上游测试套件服务（头文件库）。
- 头文件安装到 `include/foonathan/memory/`，includedirs 保持默认 `include`。
- `cmake.test()` 运行上游 doctest/CTest 套件：静态计数 42 个 `TEST_CASE`（与运行时一致），
  运行时实测 **42 例 / 164941 断言全部通过**：
  静态分布＝
  （aligned_allocator 1 / allocator_traits 2 / default_allocator 6 /
  fallback_allocator 1 / iteration_allocator 1 / joint_allocator 3 /
  memory_arena 4 / memory_pool 2 / memory_pool_collection 1 /
  memory_resource_adapter 1 / memory_stack 1 / segregator 3 / smart_ptr 1 /
  detail/align 4 / detail/debug_helpers 3 / detail/free_list 3 /
  detail/free_list_array 2 / detail/ilog2 2 / detail/memory_stack 1）。

## 状态

- W3 conan create 通过（42 例 / 164941 断言全绿），finish 门禁通过。
---

**编译结束**: 2026-09-02 03:07
**最终状态**: built
