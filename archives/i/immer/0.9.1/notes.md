# immer 0.9.1 — Bootstrap + 首轮 Adapt 笔记（pc3-39）

## 来源核验（bootstrap 阶段，官方资料确认）
- 官方仓库：https://github.com/arximboldi/immer
- 正式标签：`v0.9.1` → release commit `160f0d7025321e5dc1fc3f0b7742ca7621d43981`
  （release 页标题 "Add Nix flakes support"，为 latest release）
- 许可证：Boost Software License 1.0（BSL-1.0）
- 源码 tarball：`https://github.com/arximboldi/immer/archive/refs/tags/v0.9.1.tar.gz`
- SHA-256：`b18b92ba60ec3186dc36ef671d3c2ae542cbb63eb6dc0e258476c6111a67c971`
- codeload 直连下载 200，747070 bytes，gzip 正常解压；结构含 CMakeLists.txt / immer/ / test/ / benchmark/ / doc/ 等

## 结构
- header-only：CMake INTERFACE target `immer`，导出 `ImmerConfig`（install(EXPORT ImmerConfig …)）
- 头文件目录 `immer/`：vector / flex_vector / map / set / table / array / atom / box 等
- CMake 选项：`immer_BUILD_TESTS`(ON) / `immer_BUILD_EXAMPLES`(ON) / `immer_BUILD_DOCS`(ON) / `immer_BUILD_EXTRAS`(ON)
- 上游版本串：`project(immer VERSION 0.9.0)` —— 注意上游 CMake 版本串仍是 0.9.0，但正式发布标签为 v0.9.1（上游小瑕疵，以标签为准）
- C++ 标准：README 要求 C++14 起（config.hpp 有 C++17 分支）

## 依赖
- 无任何第三方运行时依赖（仅标准库）；可选 Boehm-GC / RRB / Boost 仅用于上游完整测试与 benchmark

## 首轮 Adapt / 本地验证
- 待执行：conan create 本地构建 + test_package smoke test（消费者验证）+ 上游 CTest 测试套件

### 对话 #1
- 适配：header-only 配方 + test_package 消费者验证（conan-verify G1-G4 PASS）
- 上游 CTest：R03 缺 Catch2 v3 前置阻塞（20/87）→ R04 以已发布 Boost/gc/fmt 恢复 87/87 Passed
- finish/W3：基线噪音隔离复验 + 完整 W3 full 模式 JC/L0 pass（Pass rate 100%）
- 交付前审计：libXext 预存修改未动未入 diff；交付仅 archives/i/immer/**（10 文件）

## 发现与知识
- ✅ immer 是 header-only C++ 库：CMake INTERFACE target `immer`，导出 ImmerConfig（cmake_file_name=Immer），无 .a/.so 产物，无需为库本身编译
- ✅ 上游 CMake 版本串仍为 0.9.0，但正式发布标签为 v0.9.1（上游小瑕疵），适配以官方标签 v0.9.1 为准（来源核验见上）
- ✅ 上游完整测试/benchmark 的可选依赖为 Boehm-GC / RRB / Boost，均非生产构建或 Conan `requires()` 依赖（依赖见上）
- ✅ 上游测试需 Catch2 v3（`catch_test_macros.hpp` / `Catch2::Catch2WithMain`）；测试前置 Catch2 v3.7.1 / Boost 1.90.0 / gc 8.2.12 / fmt 8.1.1 均仅用于上游 CTest，不入生产配方（R03-R07 实测 87/87 Passed）
- ✅ CMakeToolchain 对 OHOS 平台映射 CMAKE_SYSTEM_NAME=Linux / CMAKE_SYSTEM_PROCESSOR=aarch64（见 conanfile.py generate()，对应 E092 处理）
---

**编译结束**: 2026-09-02 19:09
**最终状态**: built
