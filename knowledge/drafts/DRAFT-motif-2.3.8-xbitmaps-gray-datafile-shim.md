# DRAFT-motif-2.3.8-xbitmaps-gray-datafile-shim：X11 家族缺失的 xbitmaps 数据文件用 include 路径 shim 补齐

> Status: Draft | Updated: 2026-09-13
> Source: motif 2.3.8 HarmonyOS PC 适配（libXm.so.4 首次适配）
> 对应：knowledge/drafts/DRAFT-motif-2.3.8-xbitmaps-gray-datafile-shim.kv
> 关键词：X11, xbitmaps, bitmaps/gray, Motif, libXm, 数据文件 shim, 非补丁修法

## 现象或适配场景

编译 Motif（libXm）时，`lib/Xm/I18List.c` 与 `lib/Xm/IconButton.c` 报：

```text
lib/Xm/I18List.c:38:10: fatal error: 'X11/bitmaps/gray' file not found
   #include <X11/bitmaps/gray>
```

`xorgproto` 已装、`libx11` 已装，头文件搜索路径正确，但该文件依然找不到。

## 根因

`<X11/bitmaps/gray>` **不是头文件，也不是库**，而是 X.Org 独立包 `xbitmaps` 提供的
源码级内联数据（内容为 `static char gray_bits[] = {0x01, 0x02};`，共 87 字节）。
X11 toolkit 把它当数据包含进 TU；链接依赖与 `-devel` 头文件集都无法满足它，而 OHOS
制品仓既没有 `xbitmaps` 配方，也没有系统 X11 安装树（无 `/usr/include/X11`）。

## 修复步骤（配方内，零补丁）

1. 在配方版本目录下放 `files/X11/bitmaps/gray`，内容用 xbitmaps 1.1.1 canonical 原文：

```c
#define gray_width 2
#define gray_height 2
static char gray_bits[] = {
   0x01, 0x02};
```

2. `exports_sources = ("files/*",)`（`export_conandata_patches()` 只带 `patches/`，不会带 `files/`）。
3. `generate()` 里把 `-I<source_folder>/files` 追加进 `CPPFLAGS`，使 `#include <X11/bitmaps/gray>` 命中。

## 验证方式

- `conan create` 全链路：configure + build + `make -C lib check` + test_package 全绿
  （motif/2.3.8：`assertions=18 failures=0`）。
- 文件内容校验：sha256 `b4df654f97ba9474c0d2b2f762c4db3d8613559447828a27f0bcfa2a0fcfc2aa`，
  与 X.Org `xbitmaps` 1.1.1 的 `gray` 逐字节一致。

## 适用范围和安全边界

适用于所有 `#include <X11/bitmaps/*>` 的 X11/Xpm 家族上游（Motif/lesstif、Xaw 系工具、
直接使用 X11 内建位图的项目）。边界：这是**数据文件 shim**，不是代码补丁——不得借它
夹带平台宏或行为修改；若上游还包含其它 X11 内建位图，必须一并补齐，不能只补报错的那一个。
