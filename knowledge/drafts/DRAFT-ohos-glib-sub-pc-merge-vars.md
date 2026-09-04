# DRAFT-ohos-glib-sub-pc-merge-vars — Conan PkgConfigDeps 生成的 glib-2.0.pc 缺变量时从原始 .pc 合并

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: 🟡 medium | **Category**: meson / pkg-config / glib / .pc

## 相关既有条目（同族差异化定位）

本 skill 与既有 "meson/glib/pkg-config" 条目共享依赖注入背景，但问题是
**.pc 变量行缺失**（datadir/glib_mkenums 等），既有条目都是链接期符号或
.pc 前缀问题——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E123**（meson 静态库 libintl） | 正式收录 | **链接期** `undefined symbol: g_libintl_*`（build.ninja 静态/动态替换） | 非本题——那是链接符号；本条目是 **configure 阶段 .pc 变量缺失** |
| **dconf 0.40.0 配方**（main 已收录） | 已收录配方 | 补 gio-2.0/gio-unix-2.0 .pc + 改写 prefix=/ | dconf 只复制 glib 子 .pc 并改 prefix，**未**踩"变量行缺失"——因为 dconf 不用 gnome.mkenums_simple，gio-2.0 Requires 链也未触发 datadir 缺失；本条目新增**从原始 .pc 合并缺失变量行**（datadir/glib_mkenums/glib_genmarshal） |

> index.tsv 查证（2026-09-02）：`Variable 'datadir' not defined` 命中 0 条、
> `glib_mkenums` 命中 0 条、`Could not get pkg-config variable` 命中 0 条——
> 无正面撞车；本条目为 dconf 模式的增量（变量行合并）。

## Scope（何时用）

在用 Conan `PkgConfigDeps` + meson 构建、依赖 glib 的软件时，若出现：

- `ERROR: Could not get pkg-config variable and no default provided for
  <PkgConfigDependency glib-2.0>`（meson 的 `gnome.mkenums_simple`/
  `gobject-query` 用 `get_variable(pkgconfig:)` 读 `glib_mkenums`/
  `glib_genmarshal`/`gobject_query`）；
- `WARNING: Pkg-config error with 'gio-2.0': Variable 'datadir' not defined in
  .../glib-2.0.pc`（gio-2.0.pc 的 `Requires: glib-2.0` 展开 cflags 时需要父包
  `.pc` 定义 `datadir`）。

典型实例：polkit/127（用了 `gnome.mkenums_simple` 且 glib 提供多个子 .pc）。

## Symptom

```text
# meson configure
../src/polkit/meson.build:44:21: ERROR: Could not get pkg-config variable and
  no default provided for <PkgConfigDependency glib-2.0: True ['>= 2.44']>
  # ← gnome.mkenums_simple 读 glib_mkenums 变量

# gio-2.0 Requires 链
WARNING: Pkg-config error with 'gio-2.0': Could not generate cflags for
  gio-2.0: Variable 'datadir' not defined in '.../glib-2.0.pc'
```

## Root Cause

1. Conan `PkgConfigDeps` 只从依赖包 `package_info` 生成 `glib-2.0.pc`——
   **不含** glib 包原始 .pc 里的变量行（`datadir`、`glib_mkenums`、
   `glib_genmarshal`、`gobject_query` 等）；
2. ①gio-2.0.pc 的 `Requires: glib-2.0, gobject-2.0, ...` 在展开 cflags 时
   需要 glib-2.0.pc 提供 `datadir`（缺则报 not defined）；
3. ②meson 的 `gnome.mkenums_simple`/`gobject-query` 用
   `get_variable(pkgconfig:)` 读 `glib_mkenums`/`glib_genmarshal`——缺则报
   "Could not get pkg-config variable"。

## Recommended Solution

**主方案：从 glib 包原始 .pc 合并缺失变量行到 generators_folder。**

在 `generate()` 里读 glib 包原始 `lib/pkgconfig/glib-2.0.pc`，提取 Conan
生成版缺失的 `key=value` 变量行（`datadir`/`glib_mkenums`/`glib_genmarshal`/
`gobject_query`/`glib_valgrind_suppressions` 等，排除 `Name`/`Description`/
`Version`/`Libs`/`Cflags`/`Requires` 头字段），合并进
`generators_folder/glib-2.0.pc` 末尾。变量值里 `${bindir}` 在 `_fix_pc_prefix`
后已指向 glib 包实际路径。

```python
# conanfile.py generate() 中
_merge_glib_tool_vars(self, glib_pkg)  # 见补丁/配方
```

**回退方案**：若无法注入 .pc 变量，改源码绕开 `gnome.mkenums_simple`
（手写 enum 头）或给 meson 传 `glib_mkenums` 全路径——改动面大，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **polkit/127** | 主验证（本 PR） | ✅ 覆盖前 meson configure 报 "Could not get pkg-config variable" + "Variable 'datadir' not defined"；合并后 generators_folder/glib-2.0.pc 含 datadir/glib_mkenums 等，94/94 编译链接成功 |

## 测试覆盖边界

- 变量合并只影响 **configure 阶段的 .pc 解析**（工具变量/Requires 链），
  不进入 package 产物，不改变库行为；
- 声明通过率时：以 conan create 全流程（configure 通过 + 94/94 编译 +
  test_package R34）为实证；polkit 上游测试按 rule 1.2 平台限制声明
  （缺 Python dbusmock）。
