# libintl 0.26.1 — 合并 libintl.so.8 双符号 shim（OHOS GI 运行时基础设施）

## 背景与动机

OHOS PC 生态缺 GI（GObject Introspection）运行时层。g-ir-scanner 是 Python
进程，必须同时加载：

- 系统 libpython（需 `libintl_*` 符号，如 `libintl_gettext`）；
- 共享 libglib-2.0.so.0（需其自带 libintl.so.8 **仅导出**的 `g_libintl_*` 9 个符号）。

两套符号风格在同一进程内互斥，`LD_LIBRARY_PATH` 只能二选一（这是项目自带
gobject-introspection 配方 `build_introspection_data=false` 的深层原因）。

## 方案

本包产出**合并 `libintl.so.8`**：同时导出 `libintl_*`（9 个）与 `g_libintl_*`
（9 个），均包装 musl libc 的 gettext 系函数。置于 LD_LIBRARY_PATH 首位，
Python 与共享 glib 均按 SONAME `libintl.so.8` 解析到本库 → 两全。

## 关键点（E 编号）

- **E077**：构建产物必须 binary-sign-tool 重签（.codesign），否则 dlopen
  Permission denied。
- **musl 链接**：`-L/lib -l:ld-musl-aarch64.so.1`（musl loader 导出 gettext 符号）。
- **无上游源码**：自研 shim，combined_libintl.c 随配方 export_sources 发布。

## 使用（消费方）

- 构建期：作为依赖使 `-lintl` 可链接（libintl.so 软链）。
- 运行期：runenv 将本包 libdir 前置到 LD_LIBRARY_PATH（消费方需置于最前）。

## 验证

- test_package：dlopen libintl.so.8 并校验两套符号集均存在（R34 实质测试）。
