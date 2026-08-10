# clang 20.1.8 适配笔记（HarmonyOS PC · 路径 A 基础适配）

## Summary

- 将 clang 20.1.8（LLVM 编译器前端）从源码构建为鸿蒙 **aarch64-unknown-linux-ohos 原生工具链**。
- 上游版本：20.1.8（release/20.x）
- 上游仓库：https://github.com/llvm/llvm-project（归档使用官方 `llvmorg-20.1.8` 发布 tarball）
- 构建方式与 llvm/20.1.0 同族策略：鸿蒙 PC 真机原生编译，不设 CMAKE_SYSTEM_NAME → 不触发交叉编译 → llvm-tblgen 原生编+跑。

## 编译环境

- 构建系统: CMake + Ninja（Release）
- 编译器: /data/service/hnp/bin/clang / clang++（设备 hnp 工具链）
- 目标三元组: aarch64-unknown-linux-ohos（默认 triple）
- 状态: built（编译通过 + conan-verify G0-G4 通过）

## 编译步骤

1. `conan source` 下载并解压 `llvm-project-20.1.8.src.tar.xz`（sha256 校验）
2. 覆盖 `llvm/cmake/config.guess` 为 stub：`#!/bin/sh\necho aarch64-unknown-linux-ohos`（设备 uname -s=HarmonyOS，config-ix.cmake 无条件调用 config.guess）
3. 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）挂到 CMAKE_MODULE_PATH（cmake 无 HarmonyOS 平台模块 → UNIX 未置 → HandleLLVMOptions FATAL）
4. cmake 配置：`LLVM_ENABLE_PROJECTS=clang`、仅 AArch64、Release、断言关、tests 不参与构建
5. `cmake --build` → `cmake --install` → 复制 SDK 资源目录（crt/builtins/libunwind/libc++ 头）→ 统一代码签名

## 源码修改（2 个 patch）

| # | Patch 文件 | 内容 |
|---|-----------|------|
| 4 | `patches/0004-lit-util-PWD-sync.patch` | lit executeCommand 将 PWD 与 cwd 同步，修复鸿蒙 bash getcwd 失败导致 lit 用例崩溃 |
| 5 | `patches/0005-gtest-port-TMPDIR.patch` | gtest CapturedStream 临时文件优先取 TMPDIR，修复只读 /tmp 下 gtest 用例崩溃 |

> 说明：早期方案曾以补丁形式处理 config.guess（umask 002 / GetHostTriple 回退）与
> runtimes CMAKE_MODULE_PATH 透传，但 build() 实际以 stub 覆盖 config.guess（输出
> aarch64-unknown-linux-ohos，与 llvm/20.1.0 同族策略），且 runtimes 不源码构建
> （从 SDK 复制）——这些补丁为死代码且含本机绝对路径，已删除（R3/R6 合规）。
> `sitecustomize.py` 禁用 `subprocess._USE_POSIX_SPAWN` 与 GNU diff/xargs 注入属于测试
> 运行环境配置（非源码改动）。

## Conan 配方要点（conanfile.py）

- **runtimes 不源码构建**：SDK libc++ 15 头与 clang 20 不兼容（nullptr_t/cmath 未定义）、musl 缺 rune table/strtoll_l、compiler-rt 交叉链接失败。对齐手工 llvm-build 先例——compiler-rt builtins / libunwind / libc++ 及 CRT 文件全部在 package() 中从 SDK 复制（`_bundle_sdk_resource_dir`）。
- **R26 合规**：不输出 libc++.so/libc++_shared.so（系统同名库），仅复制 libc++abi.a 静态库。
- **test_package**：用打包 clang 编译 test.c（校验 `__clang_major__==20`）并运行；需 CPATH 注入 sysroot C 头 + LIBRARY_PATH 注入 sysroot 库目录（打包 clang 无默认 sysroot）。
- **签名**：`_sign_binaries` 只对 ELF 文件签名（跳过 linker script 类 .so），避免 binary-sign-tool 报 "not a elf file"。

## 测试验证

- 上游 46,276 个 lit 用例（tools/clang/test 全量发现），通过 43,043（93.01%）；按适用口径（排除 Unsupported 3,157 + Skipped 13）为 **43,043/43,106（99.85%）**。
- 4 个最终未通过均为编译器行为演进（模块名大小写、输出缓冲、MC/DC 警告）或系统固有限制（只读 /tmp），非适配缺陷。

## 已知问题 / 待办

- [ ] 知识图谱草稿审查：`E228-draft-7F3A.kv`（空草稿，需填充或删除）
---

**编译结束**: 2026-08-05 19:29
**最终状态**: built
