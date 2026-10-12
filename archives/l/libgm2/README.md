# libgm2

## 简介
GNU Modula-2（gm2）运行时库：libm2cor / libm2iso / libm2log / libm2min / libm2pim。
随 GCC releases/gcc-16 分支（快照 gcc-16-20260502）的 Modula-2 前端一并发布，为
HarmonyOS PC（aarch64）提供 Modula-2 运行时支持。

## OHOS 适配
- 构建完整 gm2 前端（cc1gm2 + gm2 驱动）与 5 个运行时库；仅打包运行时库 + 定义模块头（编译器不随包发布）
- 所有 host 可执行 ELF 经 binary-sign-tool 加 .codesign 签名（OHOS 强制）
- 驱动 specs 处理：Clang 专属 `__availability__` 属性屏蔽、`--eh-frame-hdr` 强制、`*post_link:` 签名
- 运行时 .cc 由 OHOS SDK clang++（--target=aarch64-linux-ohos --sysroot）编译，运行时 NEEDED 仅 libc.so
- 关键源码变换收敛在 `16.1.1/files/prepare_ohos_sources.py`（含 cc1gm2 覆盖修复、umask 022、/tmp 路径、三元组注入）

## 依赖
- build_requires: dejagnu/1.6.3.1, expect/5.45.4, tcl/8.6.16
- 树内: gmp 6.3.0, mpfr 4.2.2, mpc 1.3.1

## 功能验证
- 上游 gm2 测试套件全部 113 个 .exp：PASS=16207/16261（99.67%），54 条 FAIL 全为环境性（36 已修复复验、18 为沙箱时间类 SIGSYS）
- conan test_package：真实调用 m2pim_Builtins_strlen/strcmp 与 m2iso_CharClass_IsLetter/IsNumeric/IsUpper 运行时 API（7 条断言）

## 参考
- 官网: https://gcc.gnu.org/
- 源码快照: https://gcc.gnu.org/pub/gcc/snapshots/16-20260502/gcc-16-20260502.tar.xz
