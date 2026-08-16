# gom

> GNOME 的 GObject 到 SQLite 对象映射库

## 简介

gom 是 GNOME 项目下的 GObject-to-SQLite 对象映射（ORM）库，将 GObject 类映射到 SQLite 表：提供 repository/adapter 抽象、资源（GomResource）、过滤器（GomFilter）、排序（GomSorting）与数据库迁移（GomRepositoryMigrator）能力。常用于 GStreamer、GNOME 应用的数据持久化层。

## OHOS 适配要点

- meson 构建（MesonToolchain + PkgConfigDeps）
- 顶层 `meson.build` 无条件 `dependency('gdk-pixbuf-2.0')`，必须提供 gdk-pixbuf 包才能 configure
- 关闭 `enable-introspection` / `enable-gtk-doc`，避免 gobject-introspection 与 gi-docgen 工具链
- glib 的 .pc 文件需补 glib_mkenums/genmarshal 变量与 `-lintl`（与 json-glib 相同处理）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | glib/gobject/gio 核心 |
| sqlite3 | 3.49.1 | SQLite 后端 |
| gdk-pixbuf | 2.44.6 | 顶层 meson 无条件依赖（test-gom-transform） |

## 功能验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package 在内存 SQLite 上执行 DDL/DML 并通过 GomCursor 回读断言
```

## 参考

- [源码仓库](https://gitlab.gnome.org/GNOME/gom)
- [GNOME 发布页](https://download.gnome.org/sources/gom/)
