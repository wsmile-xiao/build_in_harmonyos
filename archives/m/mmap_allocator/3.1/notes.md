# mmap_allocator 3.1 适配笔记

## 来源与版本核验

- 上游: https://github.com/ekg/mmap_allocator（默认分支 master）
- 任务头要求核验正式标签或 release commit：上游仅 3 个标签（mmap-allocator-0.4.0 / 0.3.1 / 0.3），无 3.1 标签，无 release；README 版本史最高 0.10.1。
- 结论：以官方 master 分支归档为源（HEAD adbfbe165d9cc21c64c61f4d5133160cbd5c2d77，2020-01-22），sha256 e1e0a7df51a10eac823fab76a7b5dbb475f61ca18de4db4bbe896e3e3d44c6c1 已核验与 conandata.yml 一致。3.1 为分析端绑定版本标识，配方归档沿用。

## 构建系统

- CMake 项目（另有 Makefile 备选），`cmake_minimum_required(VERSION 3.1)`，C++14。
- 产物：libmmap_allocator.a/.so + test_mmap_allocator 可执行；头文件安装至 include/mmap_allocator/（PUBLIC_HEADER）。
- 上游 CMakeLists 含 `-mcx16`（x86 专用）与 `set(CMAKE_BUILD_TYPE Debug)`，通过 conanfile 侧 Release 覆盖，未修改源码。

## 适配改动（3 个补丁，均 portability）

1. **0001-mmap_allocator.h.patch** — libc++ 适配：`mmap_allocator` 增加无参 `construct`/`destroy`（不写入 mmap 后备内存）与 `propagate_on_container_*` 特性。OHOS 默认 libc++，`mmappable_vector::mmap_file()` 依赖 resize 增长，若无空构造会把 mmap 区域当值写入导致崩溃。
2. **0002-mmap_file_pool.h.patch** — 补 include guard（上游头文件未守卫，被 mmap_allocator.h 间接包含 + test 直接包含时重复定义）。
3. **0003-mmappable_vector.h.patch** — libc++ 适配：`mmap_file`/`munmap_file` 改用 `resize()`/`clear()+shrink_to_fit()`（libc++ 无内部 `_M_finish` API 可操作）。

## conanfile 侧适配

- `build()` 内 `replace_in_file` 将 `cmake_minimum_required(VERSION 3.1)` 提升为 3.5：CMake >= 4 已移除 < 3.5 兼容，实测 toolchain 变量 `CMAKE_POLICY_VERSION_MINIMUM` 对 4.1.2 无效（仅 CLI -D 生效），故改源码内声明。
- `package_info()` 声明 `includedirs = ["include/mmap_allocator"]`（上游 PUBLIC_HEADER 子目录）。

## 测试

- 上游测试：`test_allocator.cpp`（CMake 目标 test_mmap_allocator），native 运行 exit 0，全部断言通过。
- test_package：消费者测试 test.cpp 覆盖 mmap 读回文件内容、文件池复用、DEFAULT_STL_ALLOCATOR 路径；修复退出顺序问题（先 munmap 再删文件，pool 记账需 stat 文件）。
- HarmonyOS 专项：conan create 以 ohos-aarch64 profile（os=OHOS, clang 15, libc++）交叉构建 + ctest 运行 test_mmap_allocator，1/1 通过。

## 依赖

- 无 requires（header + 单 cpp 的轻量库）；W0 预检通过。
---

**编译结束**: 2026-09-29 12:01
**最终状态**: built
