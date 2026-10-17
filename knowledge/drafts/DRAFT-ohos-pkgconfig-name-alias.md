# DRAFT-ohos-pkgconfig-name-alias — PkgConfigDeps 生成 .pc 文件名与 configure 期望名不一致与别名修复

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-06
> **Severity**: 🟡 medium | **Category**: pkgconfig / configure / autotools / build-system

## 相关既有条目（同族差异化定位）

本条目与既有 pkg-config/.pc 类条目共享背景，但本条目是 **PkgConfigDeps 生成文件名 ≠ configure 探测名**（.pc 命名约定差异）——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **DRAFT-ohos-glib-sub-pc-merge-vars**（polkit） | 草稿 | PkgConfigDeps 生成的 .pc **缺变量**（datadir/glib_mkenums） | 同族（PkgConfigDeps 生成 .pc 不完整），但**问题不同**——那是**文件内容缺字段**，本条目是**文件名与探测名不一致**；触发点（No package found vs 变量缺失）、修法（复制别名 vs 合并变量行）均不同 |
| **E123**（链接期 libintl） | 正式收录 | -lintl 链接缺失 | 非本题——那是 **链接期库**，本条目是 **configure 期 .pc 探测名** |
| **ats2-postiats 教训**（conan 包名不带 lib 前缀） | 记忆/社区经验 | 搜 ohpcd 时 libjansson vs jansson | 非本题——那是 **制品仓搜索命名**，本条目是 **.pc 生成名与 configure 探测名**（构建期） |

> 全库查证（2026-09-06）：`sqlite3.pc` / `sqlite.pc` / `No package 'sqlite3'` / `PkgConfigDeps.*alias` 命中 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

用 conan `PkgConfigDeps` 生成器、且上游 `configure.ac` 用 `PKG_CHECK_MODULES` 按**上游模块名**探测的库，当：

- 依赖包 conan 名 ≠ 上游 pkg-config 模块名（如 conan `sqlite/3.53.3` → 生成 `sqlite.pc`，上游探测 `sqlite3` → 找 `sqlite3.pc`）；
- configure 报 `No package '<name>' found`，即便 `conan install` 已正确装好该依赖；
- 已确认依赖确实安装（`Package requirements were not met` 里的其他包都过了）。

典型实例：zeitgeist/1.0.4（`sqlite3 >= 3.7.11` 探测失败，尽管 sqlite/3.53.3 已装）。

## Symptom

```text
configure: error: Package requirements (glib-2.0 ... sqlite3 >= 3.7.11) were not met:
No package 'sqlite3' found
```

## Root Cause

1. conan `PkgConfigDeps` 生成 .pc 时文件名取 **conan 包名**（`sqlite` → `sqlite.pc`）；
2. 上游 `configure.ac` 的 `PKG_CHECK_MODULES` 按 **上游模块名**探测（`sqlite3` → 找 `sqlite3.pc`）；
3. 二者不一致 → pkg-config 找不到 → 误报依赖缺失。

## Recommended Solution

**主方案：generate() 里把生成的 .pc 复制一份为 configure 期望名。**

零源码改动，纯构建产物命名对齐；两个名字共存（generators 目录在 PKG_CONFIG_PATH
最前，优先命中）。

```python
# conanfile.py generate() 中
import shutil
gen = self.generators_folder
if os.path.isfile(os.path.join(gen, "sqlite.pc")):
    shutil.copy2(os.path.join(gen, "sqlite.pc"),
                 os.path.join(gen, "sqlite3.pc"))
```

**回退方案**：若依赖包自带该名 .pc（如 glib 包内含 `gio-unix-2.0.pc`），把依赖包
原装 `pkgconfig` 目录 append 进 `PKG_CONFIG_PATH`——仅适用依赖包确实自带该名的情况。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **zeitgeist/1.0.4** | 主验证（本 PR） | ✅ 复制 `sqlite3.pc` 别名前 configure 报 `No package 'sqlite3' found`；别名后 `PKG_CHECK_MODULES` 通过，make 全量编译成功 |

## 测试覆盖边界

- 别名只影响 **configure 期 .pc 探测名**，不改依赖本身行为；
- 声明通过率时：以 configure 通过 + make 全量成功 + make check 10/11（log-test 因
  设备缺 D-Bus machine-id 环境限制失败，非本条目问题面）为实证。
