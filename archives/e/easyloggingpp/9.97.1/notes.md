# easyloggingpp 9.97.1 — 适配笔记

## 概览

- 上游：https://github.com/abumq/easyloggingpp
- 版本：v9.97.1（tag），源码 tarball SHA-256 `ebe473e17b13f1d1f16d0009689576625796947a711e14aec29530f39560c7c2`
- 类型：C++ 单头日志库（single-header + single .cc）
- 构建系统：CMake，需 C++14
- 语言预检：R47 lang-preflight → detected=cpp，通过
- 依赖：无外部依赖（header-only / static lib 均为零依赖）

## 关键适配点

1. **实现模式（核心）**：README 明确 "will still need `easylogging++.cc` file in order to
   compile"（issue #445 起从纯 header-only 改为单头+单源）。`ELPP_IMPLEMENTATION` 宏在
   v9.97.1 头文件中不存在。因此配方不能按纯 header-library 打包——必须编译
   `easylogging++.cc`。采用上游 `build_static_lib=ON` 产出 `libeasyloggingpp.a`，
   `package_type=static-library`，消费者链接静态库。

2. **OHOS 平台识别（E092）**：CMake 不识别 OHOS，注入 `CMAKE_SYSTEM_NAME=Linux` +
   `CMAKE_SYSTEM_PROCESSOR=armv8`。

3. **工具链 libcxx**：OHOS clang 15 需 `compiler.libcxx=libc++`；用 profile 默认的
   `libstdc++11` 会注入 `-stdlib=libstdc++` 直接报 `invalid library name`。

4. **CMake 4.x 兼容**：上游 `cmake_minimum_required(2.8.7)` 在 CMake 4.1.2 下失败
   （CMake 4 移除了 <3.5 兼容）。必须注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，且需用
   `tc.cache_variables`（configure 早期从 cache 读取，`tc.variables` 无效）。

5. **OHOS /tmp 只读（E002）**：上游测试默认日志路径 `/tmp/logs/el.gtest.log` 与配置
   文件 `/tmp/xxx.conf` 均不可写。测试构建副本将所有 `/tmp` 路径替换为可写目录
   `$HOME/tmp/elpp-test-wk/...`。适配后日志配置显式 `ToFile=true`。

6. **文件句柄陷阱**：`std::remove(日志文件)` 必须在 `reconfigureLogger` **之前**执行；
   之后删除会清掉 logger 已打开的文件句柄，日志静默丢失（0 行）。

## 测试结论

- 上游 gtest 单元测试：79 个独立 TEST 用例（26 个 suite，覆盖 24 个测试头），OHOS
  clang++ 15 + libc++ 编译并运行，**79/79 通过（100%）**，退出码 0。
- 测试入口台账：`test/main.cc` 聚合 `test/*-test.h`（24 个用户测试头 + test.h 骨架 +
  本地 wrapper `test/easylogging++.h/.cc`）；`samples/` 为示例非独立用例；构建目标
  `easyloggingpp-unit-tests`（CMake option(test)=ON）。
- 新增 HarmonyOS 专项测试 `harmonyos_test.cpp`（非空壳，15 项断言：平台识别、
  日志级别、LOG_IF、LOG_EVERY_N、行数、多 logger），编译并运行全部 PASS，退出码 0。
- 消费者验证：`test_package/test.cpp` 真实调用 LOG API 并断言日志文件内容，
  `conan create` 完整通过（5/5 PASS）。

## 版本号策略

首次适配，版本号 `9.97.1` 即上游版本。制品仓无同版本冲突。
---

**编译结束**: 2026-09-02 03:12
**最终状态**: built
