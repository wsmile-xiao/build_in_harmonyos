# DRAFT-ohos-gi18n-gettext-identity-macro — OHOS libintl.h 空 stub 下 gettext() 编译期未声明的恒等宏修复

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: 🟡 medium | **Category**: gettext / i18n / libintl / compilation

## 相关既有条目（同族差异化定位）

本 skill 与既有 "gettext/libintl" 条目共享 gettext 背景，但问题面是**编译期
头文件空 stub**，既有条目全部是**链接期符号缺失**——非重复条目；申报路径 B
时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E015**（argp-standalone） | 正式收录 | **链接期** `undefined symbol: libintl_dgettext`/`dgettext` | 非本题——E015 是 configure 检测到 libintl.h 后**链接**缺 gettext 库（LIBS="-lintl"）；本条目是**编译期** gettext 未声明（头文件空 stub），链接库不解决编译错误 |
| **E027**（-lintl） | 正式收录 | **链接期** `undefined symbol.*libintl_gettext` | 同上——链接期，非编译期 |
| **E107**（GLib static gettext） | 正式收录 | **链接期** g_libintl / libintl.a 符号 | 同上 |
| **E123**（meson 静态库 libintl） | 正式收录 | **链接期** `undefined symbol: g_libintl_*`（meson build.ninja） | 同上——meson **链接**阶段，非编译 |
| **E142**（libbytesize gnulib） | 正式收录 | **链接期** `g_libintl_dgettext: symbol not found` | 同上——NLS 重命名符号链接缺失 |

> index.tsv 查证（2026-09-02）：`undeclared function 'gettext'` 命中 0 条、
> `gi18n` 命中 0 条、`gettext=false` 命中 0 条——无正面撞车；既有 gettext
> 条目（E015/E027/E107/E123/E142）均为**链接期**，本条目为**编译期**增量。

## Scope（何时用）

在 OHOS 上编译任何 include `glib/gi18n.h` 且**关闭 NLS**（如 meson
`gettext=false`，无翻译需求）的软件时，若出现：

- 编译报 `undeclared function 'gettext'` / `implicit declaration of function
  'gettext'`（ISO C99 起为错误）；
- 报错文件分散在多个含 `_()` 调用的 .c（如 pkttyagent.c/pkaction.c/
  pkcheck.c）；
- 已确认 OHOS `libintl.h` 是空 stub（只定义 `__USE_GNU_GETTEXT` 宏，不声明
  `gettext`），且**不是**链接期符号缺失（`undefined symbol` 类错误）。

典型实例：polkit/127（authfw=shadow + gettext=false）。

## Symptom

```text
pkttyagent.c:123:24: error: incompatible integer to pointer conversion passing
  'int' to parameter of type 'const gchar *' [-Wint-conversion]
   g_strdup_printf (_("Report bugs to: %s\n"), ...)
                    ^
# gi18n.h 里：#define _(String) gettext (String)
# OHOS libintl.h 空 stub，不声明 gettext → gettext("...") 被当隐式 int
```

## Root Cause

1. glib 的 `gi18n.h` **无条件**定义 `#define _(String) gettext (String)`
   （`Q_`/`C_` 用 `g_dpgettext`，`N_` 是恒等），不检查 `ENABLE_GETTEXT`；
2. 构建未启用 gettext 时（meson `gettext=false` 不设 `ENABLE_GETTEXT`），
   `_()` 仍展开为 `gettext(...)`；
3. OHOS 的 `libintl.h` 是**空 stub**（仅 `__USE_GNU_GETTEXT` 宏），不声明
   `gettext`——clang 按隐式 int 处理，`_("...")` 返回值变 int，传给
   `const gchar *` 参数报 incompatible conversion；
4. 含 `_()` 的 .c 文件全部编译失败，且**链接库（-lintl）不解决编译错误**。

## Recommended Solution

**主方案：编译参数加恒等宏 `-Dgettext(x)=(x)`。**

让 `#define _(String) gettext (String)` 展开后变恒等：
`gettext("...") → ("...")`，`_()` 原样返回字符串——与 `gettext=false` 语义
一致，**一处修复所有 `_()` 调用点，不改任何源码**。

```python
# conanfile.py generate() 中（meson）
tc.c_args.append('-Dgettext(x)=(x)')
```

**回退方案**：非 meson 构建无法注入编译参数时，对含 `_()` 的 .c 逐文件补
`#define gettext(x) (x)` 或改 include 为 `glib.h`（不经 gi18n.h）——改动面大，
不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **polkit/127** | 主验证（本 PR） | ✅ 覆盖前 pkttyagent.c/pkaction.c/pkcheck.c 报 `undeclared function 'gettext'`（incompatible int→gchar*）；加 `-Dgettext(x)=(x)` 后 94/94 目标编译链接成功，conan create 通过 |

## 测试覆盖边界

- 恒等宏是**编译期**兼容层：只让 `_()` 在无 NLS 构建下原样返回字符串，
  不改变 gettext=false 的语义；若后续启用 NLS，移除该 c_args 即可恢复翻译；
- 声明通过率时：以 conan create 全流程（94/94 编译链接 + test_package R34）
  为实证；polkit 上游测试按 rule 1.2 平台限制声明（缺 Python dbusmock）。
