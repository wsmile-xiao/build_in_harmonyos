# g3log-2.4-cmake-ohos-sysroot — CMake 在 OHOS sysroot 下的两个可复用适配点

> 路径 B 知识草稿（与 g3log 2.4 归档同 PR 交付）。来源：g3log 2.4 第一轮适配。

## 问题 1：FindBacktrace 在未知平台（HarmonyOS）找不到 include dir

- 现象：`cmake` 配置期报 `Could NOT find Backtrace (missing: Backtrace_INCLUDE_DIR)`，
  即使 `execinfo.h` 位于编译器默认 include 搜索路径、`backtrace` 符号已在 libc 中被探测到。
- 根因：CMake 不识别 HarmonyOS 平台（无 Platform/HarmonyOS 模块），FindBacktrace 模块的
  `find_path` 无法定位 sysroot include；`FIND_PACKAGE(Backtrace REQUIRED)` 直接让整个
  配置失败，而 backtrace 能力本身（符号 + 头文件）在 OHOS sysroot 中完整存在。
- 修复：将 `FIND_PACKAGE(Backtrace)` 降级为非 REQUIRED；`Backtrace_FOUND` 为假时
  回退到编译器默认 include 搜索路径，并 `CHECK_LIBRARY_EXISTS(c backtrace "")` 后
  链接 libc（见 g3log 2.4 patches/0001-Build.cmake.patch）。
- 验证：`conan create`（ohos-aarch64 profile，clang 15）G2 PASS；本地 ctest 8/8 通过。
- 适用边界：所有在 OHOS/未知平台使用 `find_package(Backtrace REQUIRED)` 的 CMake 项目。
  注意不要在生产库中静默吞掉真正的 Backtrace 缺失——本方案仅回退 include 定位，
  符号探测仍保留（CHECK_LIBRARY_EXISTS）。

## 问题 2：配置期 ExternalProject 拉取测试框架（googletest）失败

- 现象：g3log 上游 `test_unit/Test.cmake` 在 configure 时用 ExternalProject 下载
  googletest，URL 列表含失效的 issue 链接，且下载工程 `cmake_minimum_required(2.8.2)`
  被 CMake 4.x 直接拒绝；导致 `add_subdirectory(googletest-src)` 因目录不存在而失败。
- 根因：上游下载工程版本下限过低 + URL 失效，属上游缺陷；测试框架本不是库的运行时依赖。
- 修复：补丁 0003 移除失效 URL、提升下载工程版本下限至 3.5；配方默认
  `ADD_G3LOG_UNIT_TEST=OFF`（单元测试不进入配方构建，E342 同向），本地 W3 阶段单独
  构建并完整运行上游 86 个用例（8/8 二进制全过）。
- 验证：`conan create` G2 PASS；本地 `ctest` 100% 通过（86/86）。
- 适用边界：配置期 ExternalProject 拉测试框架的 CMake 项目。若网络对下载源受限，
  优先修复下载源/版本下限；无法修复时才考虑关闭对应测试选项（E342 方案）。

## 查重差异

- 问题 1：知识图谱无 FindBacktrace/execinfo 相关条目（E222 为 ptrace 崩溃证据链、
  E457 为 glib 静态依赖，均不相关）→ 未命中，新增。
- 问题 2：E342（disable-networked-upstream-tests）方向一致但方案不同：E342 建议
  关闭联网测试，本条目是修复下载源本身（URL + 版本下限），属部分覆盖 + 新增差异。
