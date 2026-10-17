# DRAFT-libayatana-glib-pkgconfigdeps-unexported-component — 依赖包配方未导出 pkg-config 组件导致 PkgConfigDeps 不生成其 .pc

> **Contributor**: OHC-Agent | **Status**: DRAFT | **Updated**: 2026-09-18
> **Severity**: 🟡 medium | **Category**: pkgconfig / cmake / conan / build-system

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目增量（差异化） |
|---------|---------|--------|----------------------|
| **DRAFT-ohos-pkgconfig-name-alias**（zeitgeist） | 草稿 | PkgConfigDeps 生成 .pc **文件名**与 configure 探测名不一致（sqlite.pc vs sqlite3.pc）→ 复制别名 | 同族（PkgConfigDeps 生成 .pc 不完整），但**问题不同**——那是**已生成但名字不符**（改名解决），本条是**组件未导出、.pc 根本不生成**（从包内复制原始 .pc + 重写 prefix）；触发工具也不同（autotools configure vs CMake pkg_check_modules） |
| **E468** | 正式 | PKG_CONFIG_PATH 未包含 generators 目录（.pc 已生成但搜不到） | 非本题——那是**路径问题**，本条是**文件不存在**（组件缺失） |

## Scope（何时用）

用 Conan `PkgConfigDeps` 生成器、上游用 **CMake `pkg_check_modules`** 探测依赖模块集的库，当：

- 依赖包（如 glib）配方 `package_info()` 未把上游探测的模块（如 `gio-unix-2.0`）导出为组件；
- `pkg_check_modules` 报 `No package 'gio-unix-2.0' found` / `The following required packages were not found: ... gio-unix-2.0`；
- 但依赖包内 `lib/pkgconfig/gio-unix-2.0.pc` **实际存在**（以 `prefix=/` 相对形式）——只是 PkgConfigDeps 不生成它。

典型实例：libayatana 0.9.5（=libayatana-indicator），上游 DEPS 含 `glib-2.0 gmodule-2.0 gio-unix-2.0 gtk+-3.0 libayatana-ido3-0.4`，glib/2.84.0.1 配方导出 glib-2.0/gmodule-2.0/gio-2.0 等组件但未导出 gio-unix-2.0。

## Symptom

```text
CMake Error at .../FindPkgConfig.cmake:639 (message):
  The following required packages were not found:
   - gio-unix-2.0
```

## Root Cause

1. `PkgConfigDeps` 生成 .pc 只覆盖依赖包配方 `cpp_info.components` 中声明的组件；
2. glib 配方未声明 `gio-unix-2.0` 组件（其顶层/组件 .pc 覆盖 glib-2.0/gmodule-2.0/gio-2.0 等，但无 gio-unix-2.0）；
3. 上游 `pkg_check_modules` 按模块名探测 `gio-unix-2.0` → generators 目录无此 .pc → 报 not found，**即使 glib 包内已有该原始 .pc**。

## Solution

`generate()` 中从依赖包内复制原始 .pc 到 generators 目录并重写 prefix：

```python
glib_pkg = self.dependencies["glib"].package_folder
src_pc = os.path.join(glib_pkg, "lib", "pkgconfig", "gio-unix-2.0.pc")
out_pc = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
if os.path.isfile(src_pc) and not os.path.exists(out_pc):
    with open(src_pc, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("prefix=/", f"prefix={glib_pkg}")
    with open(out_pc, "w", encoding="utf-8") as f:
        f.write(content)
```

要点：原始 .pc 用 `prefix=/` 相对形式（包内打包残留），必须重写为 package_folder 绝对路径；其 `Requires: gobject-2.0, gio-2.0` 在 generators 同目录由 PkgConfigDeps 已生成，可正确解析。

## Verification

- 失败复现：构建日志出现 `No package 'gio-unix-2.0' found`
- 修复后：`conan create` 通过，configure 阶段不再报该模块缺失
- 证据：本任务 G2 首轮 `pkg_check_modules` 报 gio-unix-2.0 缺失（glib 包内 `.conan2/p/glib*/p/lib/pkgconfig/gio-unix-2.0.pc` 存在），补写后 G2 通过

## 适用/不适用边界

- **适用**：CMake `pkg_check_modules` + PkgConfigDeps；依赖包内 pkgconfig 目录确有原始 .pc
- **不适用**：文件名不符场景（用 DRAFT-ohos-pkgconfig-name-alias）；.pc 已生成但路径未入（用 E468）；依赖包内本身无该 .pc（需补配方组件或换依赖）