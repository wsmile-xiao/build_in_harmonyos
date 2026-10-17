# rumur 2026.03.11 - HarmonyOS 编译记录

## 概述

rumur 是 Murphi 形式化验证语言的模型检测器（model checker），可将 Murphi 安全协议模型编译为独立 C 验证器，并附带 murphi-format、murphi2c、murphi2xml、murphi2smv、murphi2uclid、murphi2murphi 等模型转换工具。

**编译状态**: ✅ 成功（published）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS (OpenHarmony) aarch64 |
| 编译器 | clang 15 (OHOS SDK) |
| C 库 | musl libc |
| 构建系统 | CMake (conan 2.x) |

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| gmp | 6.3.0.1 | require |
| bison | 3.8.2 | tool_requires |
| flex | 2.6.4.2 | tool_requires |
| m4 | 1.4.19 | tool_requires |

## OHOS 适配要点

1. busybox gzip 兼容（`--to-stdout` → `-c`，conanfile 内处理）
2. bison 数据目录（BISON_PKGDATADIR 指向 conan 包）
3. FlexLexer.h 头文件传播（librumur PUBLIC includes）
4. gmp SONAME 实体化（musl 不解析符号链接）
5. `/dev/stdout` ofstream 打开失败 → `patches/0001-ohos-stdout-ofstream.patch`（dup(1) 流，`__OHOS__` 守卫）

## 测试

- 上游集成测试: 4462 passed / 1209 skipped / 0 failed（5671 例）
- conan test_package: 2/2 通过

详见 `2026.03.11/reports/test-report.md`。
