# LLVM 15.0.4（HarmonyOS PC · 静态组件版）

## 软件描述

LLVM 是一套模块化、可重用的编译器和工具链技术，本包为 **15.0.4 静态组件开发包**：

- LLVM 核心库静态组件（`libLLVM*.a`，AArch64 后端）
- Clang 前端静态组件（`libclang*.a`，`LLVM_ENABLE_PROJECTS=clang`）
- 完整 CMake 导出：`LLVMConfig.cmake` / `LLVMExports.cmake` / `ClangConfig.cmake` / `ClangTargets.cmake`
- 工具：`llvm-config`、`llc`、`opt` 等（`LLVM_BUILD_TOOLS=ON`），`FileCheck`/`count`/`not`
  （`LLVM_INSTALL_UTILS=ON`）

> 本包为 AdaptiveCpp 25.10.0 提供 LLVM 15 静态依赖（R3 已证 AdaptiveCpp 需要静态归档，
> OHOS SDK 自带 LLVM 仅含共享库，118 个 `libLLVM*.a` 全部缺失）。

## 官方来源

- 项目主页：https://llvm.org
- GitHub：https://github.com/llvm/llvm-project
- Release tag：`llvmorg-15.0.4`（解析 commit `5c68a1cb123161b54b72ce90e7975d95a8eaf2a4`）
- 归档：`llvm-project-15.0.4.src.tar.xz`（官方 release 资产，110,936,424 字节）
- 归档 SHA-256：`a3112dca9bdea4095361829910b74fb6b9da8ae6e3500db67c43c540ad6072da`
  （**R6 本地实算值**；官方未发布 SHA-256，R5 已证 `official_sha256_not_published`）

## 许可证

- `Apache-2.0 WITH LLVM-exception`（源码根 `llvm/LICENSE.TXT`，官方 raw 亦核验一致）
- 本包无独立 NOTICE 文件（该 tag 下官方无独立 NOTICE；NOTICE 内容并入 LICENSE.TXT 的 LLVM Exceptions 部分）

## 构建系统与目标

| 项 | 值 |
|---|---|
| 构建系统 | CMake + Ninja（真机原生编译，不设 CMAKE_SYSTEM_NAME） |
| 目标平台 | OHOS aarch64（`aarch64-unknown-linux-ohos`，musl/LP64） |
| 静态化 | `BUILD_SHARED_LIBS=OFF`、`LLVM_BUILD_LLVM_DYLIB=OFF`、`LLVM_LINK_LLVM_DYLIB=OFF` |
| 目标架构 | `LLVM_TARGETS_TO_BUILD=AArch64` |
| 组件 | `LLVM_ENABLE_PROJECTS=clang`（AdaptiveCpp 需 Clang 组件） |
| 可选依赖 | ZLIB/ZSTD/LIBXML2/TERMINFO/LIBEDIT/LIBPFM 显式关闭（host 侧缺开发头） |

## 后续测试入口（当前未执行）

`test_package/` 仅为后续验收入口，**本轮（R8 scaffold）未执行任何构建/测试**。获批构建后应验证：

1. `conan create archives/l/llvm/15.0.4`（静态方案）成功
2. 包内存在 `lib/cmake/llvm/LLVMConfig.cmake`、`LLVMExports.cmake`、`lib/cmake/clang/ClangTargets.cmake`
3. 包内实际存在一组 `libLLVM*.a` / `libclang*.a`（导出引用可满足，首个校验 `libLLVMDemangle.a`）
4. 归档成员架构/ABI：ELF64 LE AArch64，triple `aarch64-unknown-linux-ohos`
5. AdaptiveCpp 25.10.0 以 `find_package(LLVM CONFIG)` 消费本包并完成编译

## 当前状态

- `recipe_scaffold`（R8）：recipe 文件已创建，静态方案成形，**未执行 conan create / 编译 / 测试**。
- 未经真实构建验证，所有参数以 R4/R6/R7 只读证据为依据；待授权 `conan create` 轮次实测校准。
