# DRAFT-ohos-valac-static-glib-crash — Vala 编译器静态链接 glib 启动即崩与 valac wrapper 修复

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-06
> **Severity**: 🟡 medium | **Category**: vala / toolchain / glib / runtime / ohos

## 相关既有条目（同族差异化定位）

本条目与既有"工具链运行时崩溃/动态库加载"类条目共享背景，但本条目是 **valac 静态链接 glib 的类型系统崩溃 + valac wrapper 修复**——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E179**（--disable-introspection） | 正式收录 | 构建期禁用 gobject-introspection | 非本题——那是 **构建选项**，本条目是 **valac 工具链运行时崩溃**（编译期 .vala→.c 步骤） |
| **E373**（Route build-tool introspection through Conan build env） | 正式收录 | 构建工具 introspection 走 conan 环境 | 非本题——那是 **构建工具探测**，本条目是 **valac 二进制运行时崩溃**（双 glib 类型表） |
| **DRAFT-ohos-glib-sub-pc-merge-vars**（polkit） | 草稿 | PkgConfigDeps 生成的 .pc 缺变量 | 非本题——那是 **.pc 文件内容**，本条目是 **valac 可执行文件运行时崩溃**（LD_LIBRARY_PATH 注入） |
| **ats2-postiats / psfex 教训**（ac_cv_prog_cc_cross） | 记忆/社区经验 | 交叉编译 CC 探测缓存变量 | 非本题——那是 **configure 探测**，本条目是 **Vala 编译器启动崩溃** |

> 全库查证（2026-09-06）：`cannot register existing type` / `gvaluetypes` / `G_TYPE_CHAR` / `valac.*crash` / `_g_value_types_init` 命中 0 条——无正面撞车；本条目为真增量。（xmlbird 适配用了同款 wrapper，但知识库未沉淀该错误模式。）

## Scope（何时用）

在 OHOS 上用 Vala 编译库时，若：

- 系统预装 `valac`（如 `/usr/local/bin/valac`，静态链接 glib）**任何调用**（含 `--version`）启动即崩，报 `cannot register existing type 'gchar'`；
- conan vala 包（`tool_requires`）自带的是动态链接版 `valac-0.56`，但缺 vala/glib 动态库时报 `Error loading shared library`；
- valac 默认 vapi datadir（编译期硬编码 `/usr/share/vala-0.56/vapi`）在 OHOS 不存在，`--pkg glib-2.0` 等报 `Package not found`。

典型实例：zeitgeist/1.0.4（libzeitgeist + src 引擎全部 .vala → .c 需要 valac）。

## Symptom

```text
# 系统 valac（静态 glib）——连 --version 都崩
(process): GLib-GObject-CRITICAL **: cannot register existing type 'gchar'
GLib-GObject:ERROR:../src/gobject/gvaluetypes.c:453:_g_value_types_init:
  assertion failed: (type == G_TYPE_CHAR)
Bail out! GLib-GObject:ERROR:... (core dumped)

# conan valac（动态链接版）缺库
Error loading shared library libglib-2.0.so.0: (needed by .../valac-0.56)

# valac 找不到 vapi
error: Package `glib-2.0' not found in specified Vala API directories or
  GObject-Introspection GIR directories
```

## Root Cause

1. **静态链接 glib 的 valac**：进程内存在两份 glib 类型表（静态链接 + 动态加载冲突），
   `_g_value_types_init` 断言 `(type == G_TYPE_CHAR)` 失败 → 启动即崩，与版本无关；
2. **动态链接版 valac**（conan vala 包）依赖 `libvala-0.56.so.0`/`libglib-2.0.so.0`
   等动态库，OHOS 设备系统路径没有 → 需 `LD_LIBRARY_PATH` 前置 vala 包 lib/ 与 glib 包 lib/；
3. **vapi datadir 缺失**：valac 编译期硬编码 `/usr/share/vala-0.56/vapi`，OHOS 不存在，
   需 `--vapidir=<vala 包>/share/vala-0.56/vapi` 显式指定（该目录含 glib-2.0/gobject-2.0/
   gio-2.0/posix/sqlite3 等 .vapi）。

## Recommended Solution

**主方案：conan `tool_requires("vala/<ver>")` + generate() 里建 valac wrapper。**

wrapper 脚本 `exec env LD_LIBRARY_PATH="<vala lib>/vala-0.56:<vala lib>:<glib lib>:..." <vala 包 bin>/valac-0.56 --vapidir=<vala 包 vapi> "$@"`，
`make` 用 `VALAC=<wrapper>` 编译。仿 xmlbird 配方（其已用此模式，但未沉淀为知识条目）。

```python
# conanfile.py generate() 节选（仿 xmlbird）
vala_dep = self.dependencies.build.get("vala")
vapi_dir = os.path.join(vala_dep.package_folder, "share", "vala-0.56", "vapi")
valac_bin = os.path.join(vala_dep.package_folder, "bin", "valac-0.56")
ld = f"{vala_dep.package_folder}/lib/vala-0.56:{vala_dep.package_folder}/lib"
# + glib 依赖的 lib/ 前置
wrapper = "#!/bin/sh\n" + f'exec env LD_LIBRARY_PATH="{ld}:$LD_LIBRARY_PATH" ' \
          f'"{valac_bin}" --vapidir="{vapi_dir}" "$@"\n'
# env.prepend_path("PATH", wrapper_dir)
# make VALAC=<wrapper>
```

**回退方案**：若系统 valac 恰为动态链接版（能运行），仅注入 `--vapidir`（VALAFLAGS/
AM_VALAFLAGS）即可——但 OHOS 预装常为静态 glib 版，启动即崩，通常不可用。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **zeitgeist/1.0.4** | 主验证（本 PR） | ✅ 系统 valac（静态 glib）make 启动即崩 `cannot register existing type 'gchar'`；用 conan vala 包 valac wrapper（--vapidir + LD_LIBRARY_PATH）后 libzeitgeist + src 引擎全部 .vala→.c 编译成功 |

## 测试覆盖边界

- 本条目只解决 **valac 工具链可用性**（编译期），不涉及生成 C 代码的运行正确性；
- 声明通过率时：以 make 全量编译成功 + make check 10/11（log-test 因设备缺
  D-Bus machine-id 环境限制失败，非本条目问题面）为实证。
