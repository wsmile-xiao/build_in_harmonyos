# Adaptation Notes - libgee 0.20.8

## Overview
Libgee 是 GNOME 的 GObject 集合库（Vala 编写），提供 Gee 命名空间的
集合接口与实现（ArrayList/HashMap/HashSet 等）。akira 0.0.16 依赖链的底层库。
构建系统：Autotools（configure.ac + Makefile.am）。

## Build System
- Autotools：`PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.36 gobject-2.0 >= 2.36 gio-2.0 >= 2.36)`
- 官方 tarball 自带预生成的 .c 文件（gee/ 与 tests/）与 vala stamp
  （gee/libgee_0_8_la_vala.stamp、tests/tests_vala.stamp）→ 构建无需 valac
- `VALA_CHECK([0.25.1])`：valacheck.m4 中 enable_vala 默认 no，仅当
  checkfile（stamp）缺失时强制启用 → tarball 内 stamp 存在，跳过 vala 检查
- `GOBJECT_INTROSPECTION_CHECK([0.9.0])`：默认 auto，无 gobject-introspection
  时 found_introspection=no，不报错

## 依赖（制品仓，已发布）
- glib/2.84.0 —— configure 需要 glib-2.0/gobject-2.0/gio-2.0 的 pkg-config 文件

## Build Process
1. 下载 GNOME 官方 sdist `libgee-0.20.8.tar.xz`（download.gnome.org，CI 镜像 fallback）
2. 应用补丁：0001-config.guess（HarmonyOS 检测）、0002-config.sub（ohos-linux 支持）
3. configure + make -j1
4. make check（gtester 运行 tests 测试程序）
5. make install DESTDIR=package
6. test_package: C 程序调用 GeeArrayList/GeeCollection API（add + get_size）

## OHOS 关键问题与解决
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别目标平台 | config.guess 无 HarmonyOS 分支（uname 输出 "HarmonyOS HongMeng Kernel 1.12.0 aarch64"） | 补丁 0001：config.guess 增加 `*:HarmonyOS:*:*` → aarch64-unknown-linux-ohos |
| 2 | config.sub 拒绝 linux-ohos triplet | config.sub 无 ohos-linux OS 类型 | 补丁 0002：增加 ohos-linux 基本类型 + kernel-os 校验 |
| 3 | PKG_CHECK_MODULES 找不到 glib | glib 包 pkgconfig 目录未在 PKG_CONFIG_PATH | generate() 注入 glib 包 lib/pkgconfig 到 PKG_CONFIG_PATH |
| 4 | make check 找不到 gtester | gtester 是 glib 包 bin 目录工具 | generate() 注入 glib 包 bin 到 PATH、lib 到 LD_LIBRARY_PATH |
| 5 | （潜在）valac 缺失 | configure 硬性 VALA_CHECK | 官方 tarball 自带 stamp → enable_vala=no，无需 valac（无需额外补丁） |

## 验证结果
```bash
$ make check -j1        # gtester 运行 tests（上游 C 测试套件）
$ ./test_package         # C 程序验证 gee_collection_add/get_size
```
conan-verify: 待 L0-L5 门禁验证。

## 交付物
| 文件 | 说明 |
|------|------|
| 0001-config.guess.patch | config.guess 增加 HarmonyOS 检测（同 vala 0001） |
| 0002-config.sub.patch | config.sub 增加 ohos-linux 支持（同 vala 0002） |

## 注意事项
1. 上游 tarball 已含预生成 .c 与 stamp，切勿用 git archive 替代（git 快照无 .c/stamp，会强制走 vala 模式）
2. akira 0.0.16 依赖 granite（elementary），granite 依赖 libgee → libgee 是最底层依赖
3. 头文件目录为 include/gee-0.8（非 include/），pkg-config 名 gee-0.8

---

**编译结束**: 2026-08-11
**最终状态**: built（待 PR 评审后 published）
