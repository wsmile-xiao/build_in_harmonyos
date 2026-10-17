# DRAFT-gtk2-legacy-frontend:GTK+2 时代前端库的 pc 别名困局

> Contributor: codex | Status: Draft | Updated: 2026-09-12
> Source: xsane 0.999 HarmonyOS PC 前置适配(archives/x/xsane/0.999)

## 现象

xsane 0.999 是针对 GTK+ 2 API 写成的扫描仪图形前端。它的 `configure`
通过 `AM_PATH_GTK_2_0` 宏探测 `pkg-config gtk+-2.0 >= 2.0.0`,源码中
9+ 个 `src/*.c` 文件直接使用 GTK 3 已删除的类型:
`GtkObject`、`GdkGC`、`GdkPixmap`、`GtkTooltips`、`GdkInputCondition`、
`GtkSignalFunc`。

在本仓仅有 `gtk/3.24.43` 包的条件下:

1. 配方用 PkgConfigDeps + 本地生成 `gtk+-2.0.pc` 别名
   (`Requires: gtk+-3.0`,`Version: 3.24.43`)可以让 configure 全绿;
2. `make` 阶段在 `src/xsane-back-gtk.c` 等文件编译失败,
   报上述类型 undeclared / unknown type name。

真机 shadow CI 已复现该路径:configure 通过 → `lib/` 编译通过 →
`src/` 编译失败。

## 与现有知识的关系

- E348 记录了 GNOME/GLib 家族"消费方探测非主 .pc"时用转发/别名 .pc
  解决的通用方法(如 gdk-pixbuf `_create_pkg_config_alias`)。
- 本草稿补充 E348 的**适用边界**:pc 别名只能解决"探测/配置期"缺包,
  无法弥补"API 世代差"。当源码使用目标代际已删除的 API 时,
  别名只会把失败从 configure 推迟到 make,浪费构建和真机资源。

## 方案(建议)

1. **fail-fast**:在消费方配方 `validate()` 中对受影响 profile
   (os=OHOS)抛 `ConanInvalidConfiguration`,列出具体缺失的 GTK 2 API;
   manifest 标 `status: blocked`。
2. **依赖拆分**:真正的修复是独立的 GTK+ 2 包适配
   (单独 issue/分支/PR),或显式立项目的为"xsane GTK+ 3 源码移植"的任务;
   不得混入 xsane 包 PR。
3. **保留别名与完整依赖声明**:一旦 GTK 2 包落地,删除 validate 守卫、
   把别名指向真实包即可端到端重测。

## 禁止

- 只加别名不设守卫(把失败推迟到编译中段);
- 把 GTK 2 源码/移植补丁塞进前端库 PR;
- 把"configure 通过"记成"构建通过"。

## 适用范围

所有上游探测 `gtk+-2.0`(含 `AM_PATH_GTK` 1.2 回退路径)且调用 GTK 2
专属 API 的库,在本仓仅有 gtk/3.x 包时的适配决策。
