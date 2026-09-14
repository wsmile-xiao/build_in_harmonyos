# lld 15.0.4 适配笔记

## 编译环境
- 构建系统: cmake (LLVM monorepo, LLVM_ENABLE_PROJECTS=lld)
- 编译日期: 2026-09-09
- 编译器: clang 15.0.4 (OHOS SDK toolchain) / clang++
- 状态: built

## 编译步骤

1. 官方源 `llvm-project-15.0.4.src.tar.xz`（SHA-256 `a3112dca9bdea4095361829910b74fb6b9da8ae6e3500db67c43c540ad6072da`，GitHub Release llvmorg-15.0.4）。
2. cmake configure（Ninja）：`LLVM_ENABLE_PROJECTS=lld`、`LLVM_TARGETS_TO_BUILD` 覆盖测试要求的后端（X86;ARM;AArch64;Mips;PowerPC;RISCV;Hexagon;AMDGPU;Sparc;AVR;MSP430;SystemZ）、`LLVM_DEFAULT_TARGET_TRIPLE=aarch64-linux-ohos`、`LLVM_INCLUDE_TESTS=ON`、`LLVM_BUILD_TESTS=OFF`、`LLVM_PARALLEL_LINK_JOBS=2`，TERMINFO/ZLIB/ZSTD/LIBXML2/LIBEDIT/CURL 全禁用（配方无 Conan 依赖）。
3. `build lld` + `build check-lld`（全量 lit 套件）。
4. `conan create`（OHOS aarch64 profile）完整通过：源码下载 → 4 补丁应用 → 编译 → check-lld → package → test_package（test_lld + test_ohos 签名后运行通过）。
5. `finish built` 收尾：W2 结构检查、W3 本地 CI 模拟（.ci-result.json exit_code=0）通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 aarch64:HarmonyOS | GNU config.guess 无 HarmonyOS 分支 | 补丁 0001 增加 `aarch64*:HarmonyOS:*` 分支 |
| 2 | HandleLLVMOptions "Unable to determine platform" | LLVM 平台分类仅认 FUCHSIA/UNIX | 补丁 0002 增加 `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` |
| 3 | MachO dead-strip.s 管道提前关闭 | grep -q 提前关闭管道（OHOS pipefail） | 补丁 0003 改用 FileCheck PAGEZERO 断言 |
| 4 | compact-unwind-generated.test TypeError | generate-cfi-funcs.py 用 Python2 语义 `frame_size/16`，Python3 下 `/` 返回 float 传给 randint | 补丁 0004 改 `//` 整数除法 |
| 5 | 6 个 LTO 权限类测试失败 | HMDFS 忽略 chmod u-w（已实测），无法产生 "Permission denied" | `LIT_XFAIL` 标记为 expected-fail（XPASS 仍阻塞），与 20.1.8 归档同列表 |
| 6 | 后端类测试 Unsupported（2308→206） | LLVM_TARGETS_TO_BUILD=AArch64 单后端 | 扩展为主要后端后由 REQUIRES 决定，206 个为 zlib/system-windows/xar 等平台/特性 |

## 源码修改

- patches/0001-llvm-cmake-config-guess-harmonyos.patch
- patches/0002-llvm-handle-options-harmonyos.patch
- patches/0003-lld-dead-strip-avoid-early-pipe-close.patch
- patches/0004-lld-cfi-funcs-python3-int-division.patch

## 依赖版本

- LLVM monorepo 15.0.4（仅启用 lld 项目；无需 Conan 依赖，可选集成全禁用）
- CMake 4.1.2 / Ninja / Python 3.12.9 / Conan 2.29.1（OHOS 适配版）
- OHOS SDK clang 15（aarch64-linux-ohos）

## 验证结果

```bash
# check-lld 全量（2678 用例实例化）
#   Passed: 2466, Expectedly Failed: 6 (LIT_XFAIL OHOS 权限类), Unsupported: 206, Failed: 0, Unexpectedly Passed: 0
# 通过率：2466/2679 = 92.05%（全量枚举口径）；当前配置可执行集合 2466/2466 通过
# 鸿蒙专项测试：test_package/test_ohos.c 经打包 ld.lld 链接并签名运行 → "harmonyos-lld-consumer word_size=64" (rc=0)
```

## 注意事项

- 基线隔离复验：W3 的 JC5 曾命中其他库基线文件 `archives/u/util-linux-login/2.42.2/.ci-trigger`（提交前已存在、HEAD 基线）。已按流程记录 pre_sha256、临时隔离、复跑 W3 通过、原样恢复并核对 post_sha256 一致；该路径未进入本库 diff/staged/PR。
- HMDFS chmod 权限位不生效是平台语义（并非本库缺陷），LTO 权限类测试以 LIT_XFAIL 标记。