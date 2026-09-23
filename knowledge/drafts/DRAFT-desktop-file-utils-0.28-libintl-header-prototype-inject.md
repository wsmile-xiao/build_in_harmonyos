# DRAFT-desktop-file-utils-0.28-libintl-header-prototype-inject — OHOS musl 下注入最小 libintl.h 原型声明头（保留真实 gettext 语义）

> **Contributor**: ohpcd/pc1-2 | **Status**: DRAFT | **Updated**: 2026-09-10
> **Severity**: 🟡 medium | **Category**: gettext / i18n / libintl / compilation / meson / conan

## 相关既有条目（同族差异化定位）

本 skill 与既有 "gettext/libintl" 条目共享 gettext 背景，但方案面是**编译期
原型缺失的修复方式**——既有正式条目全部是**链接期符号缺失**，草稿
DRAFT-ohos-gi18n-gettext-identity-macro 与本条目触发同源（编译期 gettext
未声明）但**方案不同**（恒等宏 vs 原型声明头）；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E015**（argp-standalone） | 正式收录 | **链接期** `undefined symbol: libintl_dgettext` | 链接期，非编译期；-lintl 不解决编译错误 |
| **E027**（-lintl） | 正式收录 | **链接期** `undefined symbol.*libintl_gettext` | 同上 |
| **E107**（GLib static gettext） | 正式收录 | **链接期** g_libintl / libintl.a 符号 | 同上 |
| **E123**（meson 静态库 libintl） | 正式收录 | **链接期** `undefined symbol: g_libintl_*` | 同上 |
| **E142**（libbytesize gnulib） | 正式收录 | **链接期** `g_libintl_dgettext: symbol not found` | 同上 |
| **DRAFT-ohos-gi18n-gettext-identity-macro**（polkit/127） | 草稿 | **编译期** gettext 未声明 | 方案不同：恒等宏 `-Dgettext(x)=(x)` **丢弃翻译语义**（适合 gettext=false 无 NLS 构建）；本条目注入最小 libintl.h **原型声明头**（gettext 家族 9 个原型 + `format_arg`），**保留真实 gettext 调用语义**（libintl.so 可链接时真实翻译），适合仍启用 NLS 或依赖真实符号的构建 |

> index.tsv 查证（2026-09-10）：`libintl.h` 注入类命中 0 条（仅 centerim 草稿提及
> -I 自身 intl 目录，机制不同）；既有 gettext 正式条目（E015/E027/E107/E123/E142）
> 均为**链接期**；恒等宏草稿为编译期但方案为丢弃翻译——本条目"编译期 + 原型声明
> 头 + 保留语义"组合无正面撞车。

## Scope（何时用）

在 OHOS 上编译任何 include `glib/gi18n.h`、meson 构建、且出现以下情况的软件：

- 编译报 `-Wint-conversion` / `incompatible integer to pointer conversion`，
  错误源是 `_("...")` 宏展开的 `gettext(...)` 被当隐式 int（20 处量级）；
- 报错文件分散在多个含 `_()` 调用的 .c；
- 已确认 OHOS `libintl.h` 不声明 gettext 家族函数（musl 无隐式声明），
  且**不是**链接期符号缺失（`undefined symbol` 类错误）；
- **仍希望保留 gettext 语义**（启用 NLS，或 libintl.so 可链接）。

典型实例：desktop-file-utils/0.28（meson + glib/2.84.0）。

## Symptom

```text
validator.c:123:24: error: incompatible integer to pointer conversion passing
  'int' to parameter of type 'const gchar *' [-Wint-conversion]
   g_strdup_printf (_("Report bugs to: %s\n"), ...)
                    ^
# gi18n.h 里：#define _(String) gettext (String)
# OHOS musl libintl.h 不声明 gettext → 隐式 int
# desktop-file-utils 实测 20 处同类错误
```

## Root Cause

1. glib 的 `gi18n.h` 无条件定义 `#define _(String) gettext (String)`；
2. OHOS musl 的 `libintl.h` 不声明 gettext 家族函数（无隐式声明机制，
   ISO C99 起 implicit declaration 是错误），clang 把 `gettext("...")` 当隐式 int；
3. `_("...")` 返回值变 int，传给 `const gchar *` 参数报 -Wint-conversion，
   含 `_()` 的 .c 全部编译失败；
4. **链接库（-lintl）不解决编译错误**；恒等宏（-Dgettext(x)=(x)）虽能消除编译
   错误，但把 gettext 变成恒等、丢弃翻译语义。

## Recommended Solution

**主方案：向 generators_folder 注入最小 libintl.h 原型声明头 + c_args -I 引入。**

让 `#define _(String) gettext (String)` 展开后 gettext 有正确原型：
`gettext("...")` 返回 `char *`（带 `__attribute__((__format_arg__))`），
`_()` 保留真实 gettext 调用——libintl.so 可链接时真实翻译，一处修复所有
`_()` 调用点，不改任何源码，不丢语义。

```python
# conanfile.py generate() 中（meson）
# 1) 写 libintl.h 到 self.generators_folder（见 .kv rec_command，9 个原型）
# 2) 让所有 C 编译可见
tc.c_args.append("-I" + self.generators_folder)
```

**回退方案**：若确认关闭 NLS（gettext=false、无翻译需求、libintl 不可链接），
用既有 DRAFT-ohos-gi18n-gettext-identity-macro 的恒等宏
`tc.c_args.append('-Dgettext(x)=(x)')`——零改动但丢弃翻译语义。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **desktop-file-utils/0.28** | 主验证（本 PR） | ✅ 覆盖前 20 处 -Wint-conversion（validator.c/install.c/update-desktop-database.c 等）；注入 libintl.h 原型头后 exit=0，test_package OK-A（--version 输出 0.28）、OK-B（合法 .desktop 校验 exit 0）、OK-C（非法 .desktop 校验 exit 1）全部通过 |

## 测试覆盖边界

- 原型声明是**编译期**兼容层：只补 gettext 家族原型，不改变 NLS 语义——
  链接期若真实 libintl 存在则真实翻译，不存在则按既有 E015/E027/E107/E123/E142
  链接期方案处理（两者正交，不冲突）；
- 声明通过率时：以 conan create 全流程（编译链接 + test_package 三段断言）为实证；
- desktop-file-utils 上游测试声明数为 0（meson 无 test 目标，全量枚举 28 文件），
  不以空测试充数；实际验证以 test_package 消费者 + 鸿蒙专项断言为准。
