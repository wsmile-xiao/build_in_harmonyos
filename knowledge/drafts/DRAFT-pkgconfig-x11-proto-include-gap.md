# DRAFT-pkgconfig-x11-proto-include-gap：pkg-config 消费链上的 X11 协议头断层

> Status: Draft | Updated: 2026-10-10
> Source: juce/8.0.5 HarmonyOS PC 适配（archives/j/juce/8.0.5）

## 规则陈述（本条增量）

凡消费方经由 **pkg-config 检测名的 Cflags** 获取 X11 头（juce_add_module 的
linuxPackages、autotools 的 PKG_CHECK_MODULES 均属此类），Conan 配方
`cpp_info.requires` 声明的 include 传递**不可达**——PkgConfigDeps 生成的
`x11.pc` 的 `Requires:` 只有 xcb：xorgproto 未声明 pkg_config_name，既不
被代生成 .pc，也不进上游库 .pc 的 Requires 链，其 include 目录因此进不了
消费方的编译命令行。

因此 X11 协议头（X11/X.h、X11/Xatom.h、X11/Xmd.h、X11/keysym.h、
X11/Xproto.h，均由 xorgproto 制品提供）要进入 pkg-config 消费方编译线，
必须同时做两件事：

1. **消费配方显式 requires**：`self.requires("xorgproto/2025.1",
   transitive_headers=True)`——版本与 libx11 依赖钉一致（避免 2024.1/
   2025.1 图内冲突），保证图内存在并把 xorgproto 自带真实 .pc 所在的
   `share/pkgconfig`（`${pcfiledir}` 相对前缀）经 buildenv_info 并入消费方
   conanbuild 环境的 PKG_CONFIG_PATH；
2. **检测名声明法**：把 `xproto` 并入 pkg-config 探测名列表——
   juce_add_module 语境写 `linuxPackages: NOLINK x11 xproto`（NOLINK 只取
   Cflags 不产生 DT_NEEDED，运行期 JUCE 全 dlopen 精确 soname）；
   autotools 语境写 `PKG_CHECK_MODULES([XPROTO], [xproto])` 或并入现有
   探测列表。pkg_check_modules/pkg-config 对缺失模块非 REQUIRED 时静默
   留空 include，必须显式列入才会接线。

一句话：**cpp_info 链修不了 pkg-config 消费链；断层要在"requires 存在性 +
pc 检测名声明"两处同时补，缺一不可。**

## 错误现象

```
/storage/.../.conan2/p/libx.../p/include/X11/Xlib.h:44:10:
fatal error: 'X11/X.h' file not found
#include <X11/X.h>
```

Xlib.h 在 libx11 包内，但它第 44 行 `#include <X11/X.h>` 指向的协议头不在
libx11 包 include 清单（仅 13 个文件：Xlib.h/Xutil.h/Xresource.h/XKBlib.h/
cursorfont.h 等），而在 xorgproto 包 include/X11/。凡源码经 Xlib.h 间接
拉起协议头的都会在此断（juce_gui_basics 还直接 include Xatom.h/Xmd.h/
keysym.h）。

## 三态探针（verification 三连，失败态可复现）

1. **失败态 A（缺 xorgproto requires）**：消费配方只 `requires("libx11/6.4.0")`，
   编译 `#include <X11/Xlib.h>` 最小 TU → `fatal error: 'X11/X.h' file not found`
   （协议头不在图内，怎么声明检测名都无源可指）。
2. **失败态 B（requires 齐全、检测名缺 xproto）**：图内已有 xorgproto，但
   linuxPackages/探测列表只写 `x11` → 同样 fatal error（xproto.pc 不进
   PKG_CONFIG_PATH 命中集或未列入探测，include 链仍断）——证明"仅显式
   requires"不构成修复，这就是 cpp_info 传递对 pkg-config 消费链失效的
   直接证据。
3. **通过态（双修齐备）**：`pkg-config --cflags xproto` 输出
   `-I<xorgproto>/include` 且最小 TU 编译通过。

## 查重与逐项差异声明

与 **DRAFT-clipboard_lite-3.4-x11-cmake-injection**（E480 系）同处
"OHOS 无系统 X11 开发树、头文件分属多制品"问题域，机制与修复面逐项不同：

| 维度 | clipboard_lite-3.4-x11-cmake-injection | 本条 |
| --- | --- | --- |
| 消费机制 | CMake `find_package(X11)` + `X11_INCLUDE_DIR`/`X11_LIBRARIES` 变量注入（tc.variables） | juce_add_module `linuxPackages` / PKG_CHECK_MODULES 检测名 → pkg_check_modules 读 .pc |
| 断裂点 | find 变量只指一个 include 目录；目录被当库路径传给 linker 被忽略 | 生成 .pc 的 Cflags/Requires 链不含 xorgproto；cpp_info.requires 对 pkg-config 消费方不可达 |
| 修复手段 | generate() 里分号拼接多制品 include、传真实 .so 文件路径 | requires xorgproto（存在性）+ 检测名声明 xproto（接线），不写任何变量注入 |
| 链接面 | 真实链接（XOpenDisplay 等符号，-lX11 DT_NEEDED） | NOLINK 零链接（运行期 dlopen 精确 soname，E505 语义） |
| 适用对象 | CMake + find_package(X11) 项目 | 一切以 .pc 检测名取 X11 头的消费方（juce linuxPackages、PKG_CHECK_MODULES） |

与图谱条目：
- **E480**（X11 头文件级依赖 transitive_headers 消费）：E480 的消费方是
  autotools PKG_CHECK_MODULES 直查 `xfixes.pc`（libxfixes 自带 pkg_config_name，
  检测名即达）；本条的消费方查的是**上游库生成 pc**（x11.pc），断裂发生在
  pc 生成侧的 Requires 链——transitive_headers 只解决"图内存在性"，接线
  还需检测名声明，此增量为 E480 所无。
- **E468**（pkg-config 模块名映射/别名）：E468 是"检测名与 .pc 名不一致"
  （名错了）；本条检测名全部正确，是 .pc 内容的 Requires/Cflags 链断裂
  （名对链断），诊断入口不同。
- **E309**（直拷源码漏打包生成头）：同"头缺失"家族。E309 是单包打包缺陷
  （包内容不完整，修 package()）；本条各包内容均完整，是跨包 include 闭包
  在消费声明层缺失（修消费方 requires + 检测名）。

## 适用边界

- 适用：一切以 .pc 检测名（linuxPackages / PKG_CHECK_MODULES / pkg-config
  裸探测）消费 X11 头的配方；协议头同类问题（wayland-scanner 系 proto、
  xcb-proto）可类推。
- 反例（forbid）：见 .kv forbid_* 字段——不得 vendor 协议头进消费方包；
  不得在消费 run 里越界改 libx11/xorgproto 配方来"修"消费链。

## 关联

E480、E468、E309、E505（NOLINK/dlopen 语义）、DRAFT-clipboard_lite-3.4-x11-cmake-injection（CMake find_package(X11) 侧互补）、
DRAFT-x11-pkgconfig-triple（x11 后端三件套硬依赖，检测名齐全性同域）。
