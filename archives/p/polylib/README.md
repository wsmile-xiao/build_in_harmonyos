# polylib

- 简介：PolyLib 是 IRISA（法国雷恩）开发的多面体运算库，处理任意维度的多面体并集，
  提供 Ehrhart 多项式、格点计数、参数化多面体分解等能力。
- 上游：<https://icps.u-strasbg.fr/polylib/>（源码发布 <https://icps.u-strasbg.fr/polylib/polylib_src/>）
- 许可证：GPL-3.0-or-later
- 构建系统：Autotools
- 目标平台：Linux、OpenHarmony PC（aarch64）
- 依赖：`gmp/6.3.0.1`（AutoDeps 注入后由 configure 自动探测）
- 默认构建三种整数表示：`libpolylib32`、`libpolylib64`、`libpolylibgmp`；
  `cpp_info.libs` 默认暴露 `libpolylibgmp`（上游 CLI 工具与 `.pc` 文件所用变体）。
- 交付形态：默认 `shared=False`，提供静态库（`libpolylib{32,64,gmp}.a`）；
  需要共享库时用 `-o polylib/*:shared=True` 构建 `libpolylib*.so`（soname `*.so.10`）。

## 交付内容

- 头文件：`include/polylib/`（`polylib32.h` / `polylib64.h` / `polylibgmp.h` 三个变体头）
- 库（默认静态）：`libpolylib32.a`、`libpolylib64.a`、`libpolylibgmp.a`
  （libtool version-info 10:1:0；`shared=True` 构建时对应 `*.so.10`）
- 工具：`c2p`、`r2p`、`findv`、`disjoint_union_sep`、`disjoint_union_adj`、
  `ehrhart_quick_apx`、`ehrhart_upper_bound`、`ehrhart_lower_bound`、
  `ehrhart_ranking{32,64,gmp}`、`ehrhart_union{32,64,gmp}`、`pp{32,64,gmp}`、
  `testehrhart{32,64,gmp}`
- pkg-config：`lib/pkgconfig/polylibgmp.pc`（静态与共享构建均安装）

## OHOS 适配

参见 [6.01/notes.md](6.01/notes.md)：config.guess/config.sub 的 HarmonyOS 三元组（E007）、
HMDFS 上 config.status 临时目录 umask（E011/E136）、NDEBUG 下 pthread 异常栈初始化修复。
