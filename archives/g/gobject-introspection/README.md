# gobject-introspection

GObject Introspection 是一个用于提供 GObject 库元数据的项目，使得其他语言可以绑定到 GObject 库。

## 版本信息

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|---------|------|
| 1.78.1 | built | 2026-05-26 | Python 扩展模块受限（E107），introspection 数据生成已禁用 |
| 1.78.1.1 | built | 2026-08-06 | 开启 introspection（gi-distutils vendoring + E212 绕行） |
| 1.80.1 | built | 2026-09-18 | **支持 glib:sync-func/async-func/finish-func 注解**，girepository 为共享库 |

### 1.80.1 与 1.78.x 的能力差异

`glib:sync-func` / `async-func` / `finish-func` 三个 GIR 注解是 **1.80.0 引入**的上游特性。
glib 的 `girparser` 只认这三个显式属性，**没有**按 `_async` 名字后缀推断的兜底逻辑，
因此在 1.78 下生成的 GIR 中，Gio 的异步方法 `is_async` 会**全部退化**为 FALSE
（上游测试 `girepository+core/callable-info` 会直接 SIGABRT）。

本机实测对照（同一份 GIR 输入分别喂给两版 `girparser`）：

| | 1.78 | 1.80.1 |
|---|---|---|
| `girparser` 中 sync/async/finish 命中 | **0** | 2 |
| `girwriter` 命中 | 0 | 2 |
| `annotationparser` 命中 | 0 | 3 |
| 对交付包的实测解析 | 属性丢失 | `async_func`/`sync_func`/`finish_func` 均正确解析 |

## 平台限制

1. **运行时需设置 LD_LIBRARY_PATH**（glib / libintl / libpython 等共享库）
2. **构建期 gir 生成**需将 giscanner 置于 conan python 的 `lib-dynload` 并签名
   （鸿蒙 loader 白名单按进程绑定，`b/`（build）与 `p/`（package）之外的共享库不可 dlopen）

## 功能说明

- `g-ir-compiler`: GIR 编译器 ✅ 可用
- `g-ir-generate`: GIR 生成器 ✅ 可用
- `g-ir-inspect`: GIR 查看器 ✅ 可用
- `g-ir-scanner`: GIR 扫描器 ✅ **可用**（1.80.1 已实测生成 15 个 GIR / 14 个 typelib）

## 交付物（1.80.1）

- 共享库：`libgirepository-1.0.so` → `.so.1` → `.so.1.0.0`
- typelib：14 个（含 `GIRepository-2.0.typelib`）
- 注：`GLib-2.0` / `GObject-2.0` / `Gio-2.0` / `GModule-2.0` 四个核心 typelib
  自 gobject-introspection 1.80 起**不再随本包安装**（上游移入 `uninstalled_gir_files`），
  它们自 glib 2.80 起由 **glib 自身**提供。

## 依赖

- glib >= 2.80.0（1.80.1 的 meson 版本闸）
- libffi >= 3.4
- meson >= 1.2.0
- flex / bison（1.80 起为构建期强制依赖）

## 参考

- [GObject Introspection 文档](https://gi.readthedocs.io/)
- [GNOME 项目主页](https://gitlab.gnome.org/GNOME/gobject-introspection)
