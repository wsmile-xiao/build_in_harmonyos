# libvidstab 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake（顶层 CMakeLists.txt 只构建 vidstab 库目标）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（conan-verify + W3 通过；待 PR 合并 CI upload 后置 published）

## 历史参考（W0b）

- 同包 1.1.2 配方（archives/l/libvidstab/1.1.2/）已合入 main 并发布制品仓，
  其 CI 加固机制（编译器路径修复 + SDK lld libxml2.so.16 运行时路径注入）
  与上游 unittest 直编方案全部沿用，仅按 1.1.0 源码差异调整（见下表）。
- 本仓库 1.1.2 的 conan create / CI 全绿经验逐项比对遵循；偏离处均已注明。

## 1.1.0 与 1.1.2 的源码差异（本次适配的核心）

| # | 差异点 | 1.1.2 | 1.1.0 | 适配动作 |
|---|--------|-------|-------|----------|
| 1 | 顶层 CMakeLists | add_subdirectory(transcode) 受 VIDSTAB_NO_TRANSCODE 控制 | 不引用 transcode/，只建库 | 无需 VIDSTAB_NO_TRANSCODE |
| 2 | FindSSE.cmake | try_compile 检测，aarch64 自动失败 | /proc/cpuinfo 检测；非 Linux/Darwin/Windows 走 ELSE 分支 → SSE2_FOUND=true | 预置 cache 变量 SSE2_FOUND=FALSE（非 FORCE 的 set 无法覆盖已存在的 cache 项） |
| 3 | sse2neon.h | 自带 | 无 | SSE2 必须保持关闭 |
| 4 | cmake_minimum_required | 3.14 | 2.6 | CMake ≥ 4 拒绝 < 3.5，加 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 5 | test_motiondetect.c 的 omp_set_dynamic(1) | #ifdef USE_OMP 守卫（已修） | 无守卫（上游 bug） | 单测编译加 `-Domp_set_dynamic(x)=((void)0)` 命令行宏，不改源码 |
| 6 | testframework.c unittest_summary() | return units_failed!=0（rc=0=全过） | return units_failed==0（rc=1=全过，语义反转） | 单测成功判定改为 rc==1 且输出含 "UNIT TESTs succeeded:" |
| 7 | 单测数量 | 13 个 UNIT TEST | 11 个 UNIT TEST（1566 checks） | 预期改为 11/11 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 配置失败：Compatibility with CMake < 3.5 has been removed | 1.1.0 的 cmake_minimum_required(VERSION 2.6) | -DCMAKE_POLICY_VERSION_MINIMUM=3.5（不改源码） |
| 2 | 若不处理，HarmonyOS 系统名下 FindSSE 会开启 SSE2 → aarch64 编译失败 | 1.1.0 FindSSE 的 ELSE 分支 set(SSE2_FOUND true) | 预置 SSE2_FOUND=FALSE cache 变量；实测输出 "Could not find hardware support for SSE2" 确认生效 |
| 3 | unittest 链接失败：undefined reference to omp_set_dynamic | 1.1.0 上游 bug：调用不在 #ifdef USE_OMP 内 | 命令行宏 -Domp_set_dynamic(x)=((void)0)（1.1.2 已在上游修复此问题） |
| 4 | unittest 全过但退出码为 1 | 1.1.0 unittest_summary 返回 units_failed==0（反转语义） | 判定 rc==1 为成功，并以输出含 SUMMARY 行佐证跑到结尾 |

## 源码修改

无补丁（patches/ 为空）。所有差异均通过 conan 配方 cache 变量与单测编译
命令行宏解决，上游源码零修改。

## 依赖版本

- 无任何 conan requires（纯 C 库，仅依赖 libc/libm）
- toolchain: OHOS SDK clang 15.0.4 + cmake 4.1.2

## 验证结果

- 探索编译：cmake -DCMAKE_SYSTEM_NAME=HarmonyOS -DSSE2_FOUND:BOOL=FALSE
  -DUSE_OMP=OFF -DBUILD_SHARED_LIBS=OFF → libvidstab.a + 16 头文件
  安装到 include/vid.stab/，成功
- 上游 unittest（tests/ 为独立 CMake 工程，用 clang 直编）：
  `clang -std=gnu99 -DTESTING -D__STRING(x)=#x -Domp_set_dynamic(x)=((void)0)
  -Isrc -Itests tests/tests.c tests/testutils.c tests/testframework.c
  src/*.c -lm -o unittest && ./unittest --all`
  → **UNIT TESTs succeeded: 11/11**（1566 checks 全过，含
  test_store_restore 1397/1397），rc=1（1.1.0 语义=全过），
  readelf 确认仅依赖 libc.so，无 libomp/libgomp
- conan create + test_package：见 reports/

## 注意事项

- 1.1.0 的 unittest 退出码语义反转（rc=1=全过）是上游已知问题，1.1.2 修复；
  下游若自行跑单测勿按惯例判 rc==0。
- conan install 用户侧头文件路径为 include/vid.stab（带点），由
  package_info.includedirs 提供，勿改成 include/vidstab（不存在）。
---

**编译结束**: 2026-09-18 18:11
**最终状态**: built（conan-verify + W3 通过；待 PR 合并 CI upload 后置 published）
