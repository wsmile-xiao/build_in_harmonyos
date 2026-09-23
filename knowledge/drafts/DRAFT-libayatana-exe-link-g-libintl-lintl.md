# DRAFT-libayatana-exe-link-g-libintl-lintl — 可执行文件链接期 g_libintl_ngettext undefined（PkgConfigDeps 生成的 glib-2.0.pc 缺 -lintl）

> **Contributor**: OHC-Agent | **Status**: DRAFT | **Updated**: 2026-09-18
> **Severity**: 🟡 medium | **Category**: linking / nls / conan / cmake / pkgconfig

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目增量（差异化） |
|---------|---------|--------|----------------------|
| **E015** | 正式 | configure 期 `undefined reference to dgettext` → `LIBS="-lintl"` | 非本题——那是 **autotools configure 传参**；本条是 **CMake + PkgConfigDeps 生成 pc 缺 -lintl**，修在配方 generate() |
| **E027** | 正式 | `libintl_gettext` undefined → `--disable-nls` | 非本题——那是 **禁用功能**（GNU 工具链）；本条库为 GTK3 图形库，NLS 是交付面 |
| **E508** | 正式 | meson + glib 静态链接 g_libintl_* → intl-wrapper 源码垫片 | 非本题——那是 **musl 无导出符号**需垫片；本场景 **glib 包内 libintl.so 已导出 g_libintl_ngettext（nm 验证 T 符号）**，缺的只是链接参数 |
| **E123** | 正式 | meson 静态库 sed 替换 .so→.a | 非本题——那是 **meson build.ninja 静态/动态选错**；本条是 CMake EXE linker flags |
| **DRAFT-glib-2.84.0.1-gettext-libintl-ld-library-path-shadow** | 草稿 | 运行时 LD_LIBRARY_PATH 遮蔽 vendored libintl | 非本题——那是 **运行时可达性**；本条是**链接期符号解析** |

## Scope（何时用）

用 PkgConfigDeps 生成 .pc、产物含**可执行文件**（非纯 .so）的 CMake 项目，当：

- 可执行文件（如 loader）链接的 .so 链（libayatana-indicator3 → libayatana-ido3）静态内嵌 glib，间接引用 `g_libintl_ngettext`；
- PkgConfigDeps 生成的 `glib-2.0.pc` Libs 行只有 `-lglib-2.0 -lm -lpthread -ldl`，无 `-lintl`；
- `ld.lld` 报 `undefined reference due to --no-allow-shlib-undefined: g_libintl_ngettext`（可执行文件默认 `--no-allow-shlib-undefined` 强制闭合）。

## Symptom

```text
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: g_libintl_ngettext
>>> referenced by .../libayatana-ido3-0.4.so
clang-15: error: linker command failed with exit code 1
```

注：主 .so（libayatana-indicator3.so）能链过（共享库默认允许 undefined），只有**可执行文件**触发。

## Root Cause

1. glib 包（PkgConfigDeps）生成的 glib-2.0.pc Libs 未携带 `-lintl`；
2. libayatana-ido3-0.4.so 构建时静态内嵌 glib，`g_libintl_ngettext` 成为其未定义符号（NEEDED 无 libintl）；
3. 链接可执行文件 loader 时，`--no-allow-shlib-undefined` 强制 .so 链全部符号闭合 → undefined reference。

与 E508 的区别：E508 场景是 musl libintl **没有** g_libintl_* 导出（需 wrapper）；本场景 `nm -D <glib>/lib/libintl.so` 显示 `T g_libintl_ngettext` 存在——只需补 `-lintl` 让链接器找到定义即可。

## Solution

主包 `generate()`：

```python
tc.variables["CMAKE_EXE_LINKER_FLAGS"] = flags + " -lintl"
```

（`flags` 为已注入的依赖图 libdir 集合，含 glib libdir，故 `-lintl` 可解析）

test_package（PkgConfigDeps 消费侧）`generate()`：给生成的 `glib-2.0.pc` 的 Libs 行追加 `-lintl`（保证消费者 test 可执行链接闭合）。

## Verification

- 复现：G2 cmake.build() 报 `g_libintl_ngettext` undefined（仅在 tools/ loader 可执行文件）
- 根因确认：`nm -D <glib_pkg>/lib/libintl.so | grep g_libintl_ngettext` → `T`（导出）
- 修复后：G2 通过；test_package 可执行链接成功、运行成功

## 适用/不适用边界

- **适用**：PkgConfigDeps + CMake + 产物含可执行文件；glib 包内 libintl.so 有 g_libintl_* 导出
- **不适用**：musl 无 g_libintl_* 导出（走 E508 intl-wrapper）；autotools configure（走 E015）；meson（走 E123/E508）