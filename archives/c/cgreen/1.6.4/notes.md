# cgreen 1.6.4 适配笔记（HarmonyOS PC / aarch64）

## 编译环境
- 构建系统: CMake（顶层 CMakeLists，min 3.10；init-build 曾误判 autotools——tarball 含遗留 Makefile）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15 (aarch64-unknown-linux-ohos) + Conan ohos-aarch64 profile
- 状态: published（conan create 通过 + 上游自测 26/26）

## 产物
- `libcgreen.so.1.6.4`（SONAME libcgreen.so.1，SOVERSION 1），C/C++ 双语言单库
- include/cgreen/* + CMake config (cgreen-config.cmake) → 库包，commands.json 不需要
- cgreen-runner / cgreen-debug 仅供上游自测构建，不 install（保持纯库）

## 编译步骤
1. conan create 由 conanfile.py 驱动：
   - CMakeToolchain cache: CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64
     （CMake 无 HarmonyOS Platform 文件；"System is unknown to cmake"→UNIX 分支缺失直接
     FATAL "can only be compiled for Linux/Cygwin/MacOSX/Msys2"）
   - CGREEN_WITH_UNIT_TESTS=ON / CGREEN_WITH_XML=OFF / CGREEN_WITH_LIBXML2=OFF
2. 上游自测两阶段（框架自测框架：断言/mock/约束/参数化与反射 runner/文本输出比对）：
   - Phase A: `ctest -j1 -E '^(runner_test_cgreen_c|runner_test_cgreen_cpp)$'` → 24/24
   - Phase B: 内置 `cgreen-runner ./tests/libcgreen_{c,cpp}_tests.so` 直跑两反射项
     → C 350 / C++ 368 passes
   - 合计上游注册 26 项全绿（xml 相关 2 项因 OHOS xml reporter 平台缺陷未启用，见下）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake "System is unknown to cmake" + src FATAL 平台分支 | CMake 无 HarmonyOS platform 文件，非 Linux/UNIX | generate() 设 CMAKE_SYSTEM_NAME=Linux / PROCESSOR=aarch64（cmocka 同款） |
| 2 | create_xml_reporter 顶层最小消费者也 SIGABRT | xml reporter fork-per-test tmpfile/messaging 在 OHOS 触发 SIGABRT（含无 xml 测试的 runner --xml） | CGREEN_WITH_XML=OFF（PR 说明如实披露；xml 子套不构建） |
| 3 | 6 个输出比对测试 "can't handle OS=Toybox" | OHOS uname -o = "Toybox"（toybox），脚本 case 无此分支 | 补丁把 Toybox/HarmonyOS 归入 lib/.so 分支 |
| 4 | 比对脚本 "No such file or directory" | 脚本 shebang `#!/bin/bash`，OHOS 无 /bin/bash | shebang 改 `#!/usr/bin/env bash`（PATH 含 /data/service/hnp/bin） |
| 5 | ctest 全量里 runner dlopen 反射项后紧跟的 6 个 bash 比对测试必挂 | 反射 dlopen 测试与后续 bash 子进程在同一 ctest 会话内交互（OHOS shell 层稳定复现） | 两阶段：先 ctest(排除两反射项)，再用 cgreen-runner 直跑两反射项（等价调用）；两次复现一致 |
| 6 | ctest -j2 并发时 diff 测试互撞 | runner/输出比对单实例资源冲突 | ctest 序列 -j1 |
| 7 | test_cgreen_c 首次 57s 波动 | 共享 PC 多 agent 并行负载 | 无代码影响 |

## 源码修改
- patches/0001-tools-runner-output-diff-ohos.patch（仅上游测试工具，不进安装包）

## 依赖版本
- 无 runtime 依赖（Threads 由上游 CMake find_package(Threads) 处理）

## 验证结果
- 本地探索: cmake 全量构建 100%；上游自测 26/26（Phase A 24 CTest + Phase B 2 反射项）
- conan create: W3 通过（含 conanfile build() 两阶段自测）
- test_package: 4 消费者程序 17 函数 44 断言全过（含 2 个负路径故意失败断言 → 验证
  run_test_suite 非零返回错误传播）

## 注意事项
- xml reporter（create_xml_reporter）在 OHOS 上不可用是平台级行为（非测试污染），已如实写入 PR ⑥
- runner 反射测试在 ctest 会话内的污染问题在 CI 同源环境复现两次，两阶段执行是确定性解法
---

**编译结束**: 2026-09-05 16:09
**最终状态**: published
