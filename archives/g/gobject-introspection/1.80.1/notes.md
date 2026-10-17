# gobject-introspection 1.80.1 适配笔记（HarmonyOS PC / OHOS aarch64）

## 为什么需要 1.80.x（1.78.1.1 无法覆盖的能力）

1.78.1① 虽能构建，但**不能生成可用的 introspection 数据**——这是 1.78 的硬限制，不是配置问题：

| 能力 | 1.78.1.1 | 1.80.1 |
|------|----------|--------|
| `glib:sync-func` / `async-func` / `finish-func` GIR 注解 | ❌ 源码中**不存在** | ✅ 完整支持 |
| Gio 异步方法 `is_async` | ❌ 全部退化为 FALSE | ✅ 正确标记 |
| `girepository-1.0` 库形态 | 需补丁改写为静态 | 上游即 `shared_library` |
| `GIRepository-2.0.typelib` | 跳过（静态库无法解析） | ✅ 正常生成并安装 |

`glib:sync-func/async-func/finish-func` 三个注解是 **1.80.0 引入**的
（官方 NEWS：「Add annotations for sync, async, and async-finish functions in the GIR」）。
glib 的 `girparser.c` 只认这三个显式属性、**没有**按 `_async` 名字后缀推断的兜底逻辑，
因此在 1.78 下生成的 GIR 中，Gio 的 279 个异步方法 `is_async` 恒为 FALSE
（上游测试 `girepository+core/callable-info` 会直接 SIGABRT）。

**本机实测对照**（同一份 GIR 输入，分别喂给两版 `girparser`）：

```
1.78  girparser.py 中 sync_func/async_func/finish_func 命中数 = 0
1.80  girparser.py 命中 2 / girwriter.py 命中 2 / annotationparser.py 命中 3
```

对交付的 1.80.1 包内 `girparser` 实测解析结果：

```
async_func  = t_obj_run_async
sync_func   = t_obj_run_sync
finish_func = t_obj_run_finish
→ ✓ 三个属性均被解析（async 不再退化）
```

## 编译环境

- 构建系统: meson + ninja（与 1.78.1.1 同一套）
- 编译日期: 2026-09-18
- 编译器: clang（OHOS SDK）
- 状态: built

## 与 1.78.1.1 的差异

### 补丁变化

| 1.78.1.1 补丁 | 1.80.1 处置 | 原因 |
|---------------|-------------|------|
| `0001-girepository-meson.build.patch`（shared→static） | **删除** | 1.80 上游即 `shared_library('girepository-1.0', ...)`，无需改写 |
| `0002-giscanner-ccompiler.py.patch`（msvccompiler 回退） | **保留** | 1.80 `ccompiler.py` 仍有 16 处 distutils 引用，`msvccompiler` 导入照旧 |
| `0003-giscanner-meson.build.patch`（条件化 `_giscanner`） | **改为内联改写** | 目标上下文在 1.80 变成展开式 `dependencies:` 块，补丁锚点失效；且本配方 `build_introspection_data=true` 下该补丁为功能空操作 |
| `0004-meson.build.patch`（harmonyos 平台 + tests 闸） | **改为内联改写** | 同上：改用 `build()` 内 `replace_in_file` 风格，不受上下文格式影响 |

### 新增构建前置

1.80 的 `giscanner/meson.build` **强制**要求 flex/bison（1.78 无此要求）：

```meson
flex  = find_program('flex', 'win_flex')
bison = find_program('bison', 'win_bison')
```

故新增 `tool_requires("flex/2.6.4.2")` 与 `tool_requires("bison/3.8.2")`（ohpcd 均有制品）。

### 上游交付变化（须如实反映，非本适配裁剪）

1.80 把 **GLib-2.0 / GObject-2.0 / Gio-2.0 / GModule-2.0** 的 GIR 从 `gir_files`
移入 **`uninstalled_gir_files`**——即**不再随包安装**。这四个核心 typelib 自
glib 2.80 起由 **glib 自身**提供。故本包不再交付它们，`test_gi.py` 的断言
相应改为本包真正交付的 `GIRepository-2.0` + 预置第三方 typelib。

### gi-distutils 裁剪（147 → 24 文件，提交 92e68f5e）

`gi-distutils/` 最初是 1.78.1.1 的整体拷贝——setuptools 的完整 vendored 树
（147 文件，含 autocommand/backports/wheel/typeguard 等本包用不到的附带包）。

本版本改为**只保留 giscanner 实际 import 的运行时闭包**（24 文件）：

```
distutils/{__init__, _log, _macos_compat, _modified, _msvccompiler, ccompiler,
          cygwinccompiler, debug, dep_util, dir_util, errors, file_util, spawn,
          sysconfig, unixccompiler, util, version}.py
distutils/compat/{__init__, py38, py39}.py
jaraco/functools/__init__.py
more_itertools/{__init__, more, recipes}.py
```

- 裁剪依据：conan python（无 setuptools 劫持）下实测 `giscanner` 的
  distutils 引用全部落在上述闭包内；`import distutils.cygwinccompiler` 等
  8 处 import 均被覆盖。
- 验证：裁剪后 `conan create` 全绿——gir 生成 104/104、上游 scanner
  测试 9/9、test_package 10/10、`EXIT=0`。
- 附带收益：PR 体量从 **158 文件 / 47142 行** 降到 **35 文件 / ~12600 行**，
  避免触发平台评审体量上限（约 152 文件/46200 行即跳过 AI 评审）。
- 注意：conan 2 的 `exports_sources` **禁止 `..` 相对路径**，故无法让
  1.80.1 引用 1.78.1.1 的 gi-distutils 实现跨版本共享；裁剪是唯一合规路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_program('flex')` 报错 | 1.80 新增强制依赖 | `tool_requires` flex/2.6.4.2 + bison/3.8.2 |
| 2 | Python ≥3.12 硬检查 `modules: ['setuptools']` 失败 | conan python 不带 setuptools（实测两版均无） | 注释掉该检查，沿用 1.78.1.1 已验证的 vendored `gi-distutils/` 方案 |
| 3 | `tests` 闸在 1.80 只剩 `is_cross_build()` | 上游简化了闸条件，1.78.1.1 的锚点文本已不存在 | 按 1.80 真实文本内联改写为 `if false and ...` |
| 4 | `host_system == 'harmonyos'` 未归入 linux 分支 | 平台判定只列 linux/darwin | 内联改写为 `(host_system == 'linux' or host_system == 'harmonyos')` |
| 5 | `g-ir-compiler` 运行报 `Error loading shared library libgirepository-1.0.so.1` + 一串 `symbol not found` | 签名 glob 用 `**/*.so`，**漏掉版本化实体库** `libgirepository-1.0.so.1.0.0`（不以 `.so` 结尾）→ dlopen `Permission denied` | 三处签名 glob 改为 `**/*.so*`（非 ELF 由 `_sign_elf` 的 ELF magic 检查跳过） |
| 6 | scanner 上游测试 1/9（8 个 `No module named 'giscanner'`） | 1.80 首次 `meson.build()` 即成功，**不再走 E212 兜底分支**，而该分支顺带完成「giscanner 复制进 python lib-dynload 并签名」 | 在 `else` 分支显式调用 `_install_giscanner_to_package()`；实测恢复 9/9 |
| 7 | 首次 configure 报 `Python.h` / `glib-2.0` include 路径为 `//include/...` | 依赖 `.pc` 的 `prefix=/` 无效 | 沿用本仓既有做法（native file 钉 conan python + 修正 `.pc`） |

> 注 5 是**真缺陷**且 1.78.1.1 从未暴露：1.78 的 girepository 是静态库，
> 根本不存在版本化 `.so` 文件，故签名 glob 的漏配被掩盖。

## 验证结果

### 交付物

| 项 | 内容 |
|----|------|
| 共享库 | `libgirepository-1.0.so` / `.so.1` → `.so.1.0.0`（真实共享库，非静态） |
| typelib | 14 个（含 **`GIRepository-2.0.typelib`**） |
| 工具 | `g-ir-scanner`（`--version` 输出 **1.80.1**）、`g-ir-compiler`、`g-ir-generate`、`g-ir-inspect` |

### 本地实测（`conan create`）

- 主包：`Package 'd183c9baf03e5f46911237ae9e5caec45d2e4f19' created`，`EXIT=0`
- test_package：`test_gi.py` 9 项断言全 PASS + `g-ir-compiler --version` 实际运行 PASS
- 上游测试：`UPSTREAM-SCANNER-TESTS: 9/9 passed, 0 failed`；
  `UPSTREAM-WARN-TESTS: 19/19 passed, 0 failed`（warn 组为本版新增实测）

### 未运行项归因（逐条证据）

上游 `tests/` 中 `offsets` / `repository` **两组**在 1.80 下**可以链接构建**
（与 1.78 不同——1.78 因 girepository 为静态库而链接失败），但**运行仍不通过**，
证据如下：

```
$ ./tests/repository/gitestrepo
** (process:18246): ERROR **: Typelib file for namespace 'Gio' (any version) not found
Signal 5 (core dumped)   # G_DEBUG=fatal-warnings → 警告即 abort
```

根因：这两组是**编译型 C 测试**，运行期需要 `GLib`/`GObject`/`Gio` 的 typelib，
而它们（见上「上游交付变化」）由 glib ≥2.80 提供；本仓 glib 配方显式
`introspection = "disabled"`（0 typelib），故运行期无法加载。
`gitestoffsets` 另需两个命令行参数（用法：`gitestoffsets COMPILED INTROSPECTED`）。
（offsets 1 + repository 4 = **5 项**。）

### warn 组（19 项）**已实测通过** —— 与上两组不是一类

上一版把 warn 组与 offsets/repository 一起当作「需 typelib」裁剪，该归因**不成立**：
`tests/warn/warningtester.py` 是**纯 Python**，只 `import giscanner.*`
（`SourceScanner` / `Transformer` / `MainTransformer` / `IntrospectablePass` /
`MessageLogger` / `GtkDocCommentBlockParser`），**不加载任何 typelib、不 dlopen
上游共享库**；19 个夹具唯一的系统依赖是 `common.h` 的 `<glib-object.h>`，而 glib
是本配方现成依赖。

故本版在 `conanfile.py` 新增 `_run_upstream_warn_tests()`：按上游
`tests/warn/meson.build` 的 `warn_tests` 列表（**解析获得，不硬编码**，解析不到即报错）
逐个运行 `warningtester.py <fixture.h>`，逐条比对夹具内 `// EXPECT:` 声明的期望告警
（数量与文本均须一致，否则非零退出）。**实测 19/19 通过**，失败即阻断构建。

需要的特殊 env（与 meson 注册该测试时一致）：`UNINSTALLED_INTROSPECTION_SRCDIR`、
`TOP_BUILDDIR`（同时是其 gir 搜索路径之一 —— `top_builddir/gir` 下有构建期生成的
`GObject-2.0.gir`）、`PKG_CONFIG_PATH`（脚本内部 `process_packages(['gobject-2.0'])`
取 Cflags 喂预处理器）。

### 计数口径修正（上一版少算 18 项）

上一版 `full_test_denominator.total_all` 写 **82**，其中把 warn 组记成 **1**
（只数了脚本文件 `warningtester.py`），而同表 offsets/repository 用的是「meson 注册的
`test()` 目标数」—— 三个组**计量单位不一致**。按同一把尺子 warn 应为 **19**
（`warn_tests` 列表 19 项，`foreach` 各注册一个 `warn-<name>`）。故全量分母
= 76 + 1 + 4 + 19 = **100**。

**结论**：可运行的上游子集已实测并如实填报（scanner 76 + warn 19 = **95 项全通过**）；
其余 **5 项**（offsets 1 + repository 4）按上述可复现证据逐条归因，不以 skip/xfail 掩盖。

## 关键依赖

- glib >= 2.80.0（1.80 的 meson 版本闸；本仓 ohpcd 有 2.84.0.1 / 2.88.0 等 8 个版本）
  - 实际选用 **2.84.0.2**：本配方 force 了 libffi/3.5.2 + zlib/1.3.1.1.1.1，使 glib 的
    package_id 与 ohpcd 制品不匹配 → CI 会从源码重建 glib，而 2.84.0.1 在 CI 环境
    构建失败（gettext libintl 遮蔽 → `g_libintl_*` 符号重定位失败）。
    2.84.0.2 已把子项目 proxy-libintl 静态化（产物无 `NEEDED libintl.so.8`），
    正是为修此 CI 失败发布的版本，且已在 main + ohpcd，属既有版本。
- meson >= 1.2.0
- python >= 3.8（>=3.12 时上游要求 setuptools，见问题 2）
- flex / bison（构建期，1.80 新增）
