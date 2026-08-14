# libpsl 0.21.5.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libpsl.so 等 1 个库，供链接与 dlopen。

## 关键适配

**未打任何补丁。** 上游源码直接可用鸿蒙 PC 原生工具链构建。

值得对照：仓内手工构建时代的 `libpsl/0.21.5` 条目带着 patches 目录，本包一个都不需要。

## 版本号说明

版本取 **0.21.5.1** 而非 0.21.5：`archives/l/libpsl/0.21.5` 已是手工构建时代的
条目（`status: built`，带 patches，无 conanfile.py）。按仓内 repack 惯例
（zlib 1.3.1→1.3.1.1、libidn2 2.3.7→2.3.7.1）另起版本号做 conan 化，
**不改动那个既有条目**。源码仍是上游 0.21.5。

## 选项取舍

- `--enable-runtime=libidn2` / `--enable-builtin=libidn2`：运行时 IDNA 用
  libidn2（IDNA2008，也是上游默认）。**不选 libicu**（仓里没有对应包）、
  **不选 libidn**（那是过时的 IDNA2003）。libidn2 另需 libunistring，已一并声明。
- `--disable-gtk-doc`：文档不进制品。

产物版本串为 `0.21.5 (+libidn2/2.3.7)`，可据此确认 IDNA 后端确实接的是 libidn2。

## 依赖与合入顺序

依赖 `libidn2/2.3.7.1`（本人 PR #4592 在途）与 `libunistring/1.0`（已在架）。
**CI 需等 #4592 合入并发布后再触发**，否则拉不到 libidn2。

## 状态

built（真机 conan create + test_package 通过）
