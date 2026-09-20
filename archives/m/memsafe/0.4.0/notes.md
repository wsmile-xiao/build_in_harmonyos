# memsafe 0.4.0 适配笔记

## 编译环境
- 构建系统: NetBeans Makefile 项目（nbproject/），库本体为 header-only（memsafe.h）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / libc++ (OHOS SDK llvm)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build memsafe 0.4.0 --url=https://github.com/rsashka/memsafe/archive/refs/tags/v0.4.0.tar.gz`
   - 官方 tag v0.4.0，SHA-256 861afa198eae1550cab44a8d3b8dce4bc05216bf9e8d4f8c27beece4f9a3e34c
2. `ohc-run.py lang-preflight memsafe 0.4.0` → detected=cpp，匹配
3. 配方按 header-only 库形态编写（conanfile.py + test_package + patches）
4. `ohc-run.py conan-verify memsafe 0.4.0` → G1/G2/G3/G4 全 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | memsafe.h 使用 `std::format`，OHOS clang 15 libc++ 无 `__cpp_lib_format`（std::format 不可用） | 上游要求 C++20 std::format，OHOS SDK LLVM15 libc++ 未实现 | 补丁 0001：`#ifndef __cpp_lib_format` 守卫 + 本地 `ms_fmt1` 单占位符替换函数 |
| 2 | memsafe.h 中 `T::ValueType` 依赖类型缺 `typename` | clang 15 严格要求 typename（clang 20 上下文宽松） | 补丁 0001：3 处补 `typename` |
| 3 | 上游 clang 插件（memsafe_clang.so）目标 clang-20 API（AS_C23、handleStmtAttribute override 签名等） | 本机仅 clang 15.0.4，插件 API 不兼容 | 插件为开发期静态分析工具，非库交付物；header-only 库本体不依赖插件，不打包 |

## 源码修改

- patches/0001-memsafe.h.patch：memsafe.h 增加 __cpp_lib_format 守卫与 ms_fmt1 替代 std::format，补齐 3 处 typename

## 依赖版本

- 无运行时依赖（header-only）
- 测试依赖（本地验证）：gtest 1.17.0.1、yaml-cpp 0.8.0（均来自 ohpcd 制品仓，本机 clang 15 二进制）

## 验证结果

### 消费者验证（test_package，test.cpp）
- 调用 memsafe.h 公开 API：memsafe::Shared<int> / lock() / weak() / set()
- 编译链接运行通过，输出 `test_memsafe: OK (shared=7, weak=7)`，exit 0

### 上游测试台账（gtest，memsafe_test.cpp）
- source_declared_total: 11（MemSafe.Sizes/Cast/Class/Threads/Depend/ApplyAttr/Separartor/MemSafeFile/WeakList/Plugin/Cycles）
- configured_executable_total: 11（单二进制 memsafe_unittest，gtest 注册全部 11 项）
- executed_passed_total: 8
- 失败 3 项：
  - Sizes：OHOS libc++ ABI sizeof 断言差异（std::string=24 而非上游假设 32，variant/runtime_error 同理）——平台 ABI 差异，非库缺陷；SyncTimedMutex/Shared 尺寸断言同样受影响
  - Plugin：需要 clang-20 + memsafe_clang.so 插件（本机仅 clang 15，插件 API 面向 clang 20）→ 工具链硬阻塞
  - Cycles：同上（circleref 分析需插件）
- 通过率：8/11 = 72.7%（全量口径）；8/11 = 72.7%（实际执行口径，11 项全部实例化执行）
- 恢复条件：获得 clang-20 工具链后可构建插件并补跑 Plugin/Cycles；Sizes 需按 OHOS libc++ ABI 调整断言

### 日志
- 上游测试运行日志：见 reports/（gtest 完整输出）
---

**编译结束**: 2026-09-19 21:26
**最终状态**: built
