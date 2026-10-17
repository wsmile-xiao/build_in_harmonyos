# DRAFT-ohos-gi-180-gir-uninstalled — gobject-introspection 1.80 起核心 GIR 移入 uninstalled_gir_files，不再随包安装

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-18 | Severity: 🟠 major
> Source: gobject-introspection 1.80.1（PR #10682）——交付物核验：GLib/GObject/Gio/GModule typelib 缺失

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|---------|--------|--------------------------|
| E429 | 已收录 | 消费者运行时视角：OHOS 制品仓/系统镜像**无 .typelib**，`gi_repository_require` 必然失败 | 本 skill 是**上游交付变更**：1.80 起 GI 包**本来就不该**再交付 4 个核心 typelib（移入 `uninstalled_gir_files`），改由 glib 提供。E429 描述「生态缺 typelib」的现状，本 skill 说明「GI 1.80 之后的交付边界」——若 glib 仍未开 introspection，两者叠加才导致运行期失败；**不得**把上游变更当成自己的裁剪来「修复」 |
| E430 | 已收录 | 消费者依赖图 zlib 版本冲突 | 无重叠 |
| DRAFT-ohos-gi-annotations-require-180 | draft（本次同批） | 注解能力缺口（1.78 无 sync/async/finish-func） | 本 skill 是**交付物集合变化**（哪些 typelib 随包安装），与注解能力正交；两者都是 1.80 适配的独立知识面 |

**撞车判定**：全库查证 `uninstalled_gir_files`（0 命中）、`GLib-2\.0\.typelib.*not found` 相关（0 命中）。E429 是消费者视角现状，未覆盖「1.80 上游把核心 GIR 移入 uninstalled_gir_files」这一上游行为变更，作为独立条目申报。

## Scope（何时用）

- 适配 gobject-introspection **≥ 1.80**，或消费其产物的配方/测试
- 包内 `lib/girepository-1.0/*.typelib` 清单与 1.78.x 不同（17 个 → 14 个，缺 GLib/GObject/Gio/GModule）
- 上游 C 测试组（offsets/repository/warn）报 `Typelib file for namespace 'Gio' not found`

## Symptom

```
# 1.80.1 包内 typelib 清单（对比 1.78.1.1 的 17 个）
DBus-1.0 DBusGLib-1.0 GIRepository-2.0 GL-1.0 Vulkan-1.0 cairo-1.0
fontconfig-2.0 freetype2-2.0 libxml2-2.0 win32-1.0 xfixes-4.0 xft-2.0
xlib-2.0 xrandr-1.3        ← 共 14 个，**无** GLib/GObject/Gio/GModule

# 依赖核心 typelib 的 C 测试运行期
** (process:...): ERROR **: Typelib file for namespace 'Gio' (any version) not found
Signal 5 (core dumped)   # G_DEBUG=fatal-warnings → 警告即 abort
```

## Root Cause

1. 上游 1.80 把 `gir/meson.build` 中四个核心 GIR（`glib_gir` / `gobject_gir` / `gmodule_gir` / `gio_gir`，L256/322/358/469 附近）从 `gir_files +=` 改为 **`uninstalled_gir_files +=`**。
2. `gir_files` 随包安装（生成 `.gir` 与 `.typelib`）；`uninstalled_gir_files` **仅用于构建期自测、不随包安装**。
3. 上游意图：自 **glib 2.80** 起这四个核心 typelib 由 **glib 自身**（`-Dintrospection=enabled`）构建交付，GI 不再重复安装。
4. 连带影响：1.80 下依赖核心 typelib 的 C 测试组（offsets/repository/warn）**可以链接构建**（girepository 已是共享库，1.78 时因静态无法链接），但**运行期**仍因缺 glib 提供的 Gio typelib 失败——本仓 glib 配方 `introspection = "disabled"`（0 typelib）时必然如此。

## Workaround / 修复

- **如实归因**：这是上游行为变更，**不是**本适配裁剪——不要为了凑交付物而把 `uninstalled_gir_files` 改回 `gir_files`（会与 glib 的交付重复/冲突）。
- 若 glib 配方 `introspection=disabled`：依赖核心 typelib 的运行期测试（offsets/repository/warn）按可复现证据逐条归因（`Typelib file for namespace 'Gio' not found` + `G_DEBUG` abort），**不用 skip/xfail 掩盖**。
- `test_gi.py` 断言应改为本包真正交付的 `GIRepository-2.0` + 预置第三方 typelib。

## Prevention

- 提 GI ≥ 1.80 的 PR 前，先核对上游 `gir/meson.build` 中 `gir_files` vs `uninstalled_gir_files` 的归属，避免沿用 1.78 的交付预期。
- 申报口径：交付物清单写「14 个 typelib」并注明不含 4 个核心（由 glib 提供）。

## References

- PR #10682（GI 1.80.1）
- E429（OHOS 无 .typelib 生态）
- glib ≥ 2.80 introspection 移交（上游 gir/meson.build）
