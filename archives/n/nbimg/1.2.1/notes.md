# nbimg 1.2.1 — 适配笔记

## 软件信息
- 上游: https://github.com/poliva/nbimg（官方 tag `v1.2.1`）
- 语言: C（GPL-3.0-or-later，兼容 GPLv3+）
- 构建系统: 纯 GNU Make（无 configure），单文件 `nbimg.c`
- 产物: `nbimg` 命令行工具（NB/IMG <-> BMP 转换，含 HTC NBH 打包）

## 上游测试清点（R51 三步法）
1. **清点**：上游源码包仅含 `nbimg.c`、`Makefile`、`README.md`、`LICENSE`，
   无 tests/ 目录、无 ctest/pytest 注册、Makefile 无 check/test 目标 → 上游无测试套件。
2. **运行**：受上游限制无可运行的官方测试；以功能往返转换作为等价验证
   （BMP→NB→BMP 字节级尺寸断言）。
3. **回填**：test_package 执行真实二进制往返冒烟测试（详见下"验证"）。

## 适配决策
1. **跳过 win32 目标**：上游 `all: nbimg win32`，其中 `win32` 目标调用
   `i586-mingw32msvc-gcc` 交叉编译，OHOS 构建沙箱无此工具链。配方直接
   `make -j1 nbimg`，仅构建原生目标（纯 Makefile 目标选择）。
2. **in-source 构建**：上游 Makefile 无 VPATH，无法 out-of-source；
   配方 layout 设 `folders.source = folders.build = "."`。
3. **不走 `make install`**：OHOS 构建沙箱缺少可用的 GNU coreutils
   `install`；package() 直接 conan copy 二进制与 README/LICENSE。
4. **无依赖**：nbimg 仅使用标准 C/POSIX 接口（stdio/getopt/unlink），
   无需 `requires`。
5. **LP64 补丁**：`convertNB2BMP` 用 `unsigned long biSize` 写 BMP DIB 的
   `biSize`（图像数据大小）字段，BMP 规范要求 4 字节。OHOS aarch64 为 LP64
   数据模型（`long` = 8 字节），`fwrite(&biSize, sizeof(biSize))` 会多写 4
   字节，导致 NB→BMP 产物比预期大 4 字节（230458 ≠ 230454）。以补丁改为
   `unsigned int biSize`，保证 32 位平台与 LP64 平台产物字节一致、头部合法。

## 编译命令（等价于配方 build()）
```sh
make -j1 nbimg CC=clang CFLAGS="-fPIC -O2"
```

## 验证
- **本地原生编译**（Windows x86_64 / MinGW-w64 gcc 16.1.0）编译通过，
  仅上游同款 -Wsign-compare/-Wstringop-truncation 警告。
- **往返转换测试**：
  - BMP→NB：320x240 24bpp（230454 字节）→ 输出 NB 262144 字节
    （153600 像素 + 108512 padding + 32 字节 HTC 签名）
  - NB→BMP：QVGA 自动识别（240x320）→ 输出 BMP 230454 字节
  - 两方向转换均 exit 0，产物尺寸与预期完全一致
- **LP64 复现与修复**（Linux x86-64，与 OHOS aarch64 同为 LP64）：
  - 未打补丁：NB→BMP 输出 230458 字节（`unsigned long`=8 字节写穿 BMP 头部）
  - 应用补丁：NB→BMP 输出 230454 字节，与 test_package 断言一致
- **aarch64-ohos 交叉编译**：原始与补丁源码均可用 OHOS clang 15 编译通过；
  完整构建与 test_package 由 PR CI 流水线执行验证。

## 关键命令
- conan create: 见 conanfile.py（无 requirement）
- test_package: `nbimg -F <bmp>` / `nbimg -F <nb>` 往返 + 尺寸断言
---

**编译结束**: 2026-09-05
**最终状态**: built