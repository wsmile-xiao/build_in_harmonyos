# E-DRAFT: OHOS sysroot 的 libintl.h 是空壳头——仅凭 HAVE_LIBINTL_H 判定会翻车

- **触发实例**：trueprint 5.3 适配（2026-09-13，任务 13410，分支 feat/trueprint-5.3）
- **错误签名**：`implicit declaration of function 'gettext'` →
  `incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *'`
  → 链接期 `undefined symbol: gettext`
- **类别**：legacy-source-compat
- **严重度**：2（编译+链接双阶段确定性失败，修复模式固定）

## 症状

```text
src/diffs.c:169:20: warning: call to undeclared function 'gettext'
src/getopt.c:672:23: error: incompatible integer to pointer conversion
                      passing 'int' to parameter of type 'const char *'
  # define _(msgid)       gettext (msgid)
...
ld.lld: error: undefined symbol: gettext
>>> referenced by diffs.c ... referenced 59 more times
```

## 根因

OHOS musl sysroot 自带的 `/usr/include/libintl.h` 是**空壳**：只有宏定义
（`__USE_GNU_GETTEXT`、`__GNU_GETTEXT_SUPPORTED_REVISION`），**不声明任何函数**。

于是 autoconf 的检测结果出现「半真半假」组合：

| 探测 | 结果 | 说明 |
|---|---|---|
| `AC_CHECK_HEADERS(libintl.h)` | ✅ 成功 | 文件存在 → `HAVE_LIBINTL_H=1` |
| `AC_CHECK_FUNCS(gettext)` | ❌ 失败 | 库里没有 → `HAVE_GETTEXT` 未定义 |

而老 GNU 源码（trueprint 5.3 的 `replace/replace.h` 与 `src/getopt.c`，同代包
普遍如此）只用 `#ifdef HAVE_LIBINTL_H` 一个宏决定「信任系统头还是走本地
声明」。空壳头让代码走进「信任」分支却拿不到任何声明：gettext 变隐式 int →
编译错误；即使绕过编译，`AC_REPLACE_FUNCS(gettext)` 准备好的自带实现
（replace/libreplace.a）在 glibc 上游从不需要链入（gettext 在 libc 里），
OHOS 上也没有人链它 → `undefined symbol: gettext`。

## 最小修复（两部分，平台无关）

1. **声明层**：把所有 gettext 声明/包含分支的守卫从单宏改为双宏——

   ```c
   #if defined(HAVE_LIBINTL_H) && defined(HAVE_GETTEXT)
   # include <libintl.h>
   #else
   char *gettext(const char *);
   #endif
   ```

   glibc 上两个宏同时定义，行为不变；OHOS 上回落到本地声明。

2. **链接层**：用 make 变量覆盖把自带实现链入主程序，不改生成的
   Makefile.in：

   ```bash
   make LDADD="../replace/libreplace.a"    # noinst 归档，AC_REPLACE_FUNCS 产物
   ```

已验证：补丁后 trueprint 5.3 在 OHOS aarch64 真机 `conan create` 干净构建
通过，上游 49/49 测试全过（conan-verify G0-G4/L2/L4/L5 全绿）。

## 禁忌

- 禁止手改 config.h 强塞 `HAVE_GETTEXT=1`（掩盖探测真相，i18n 静默失效）；
- 禁止用宏 `#define gettext(msgid) (msgid)` 或 dummy 符号糊弄链接；
- 仅当包真的需要运行时 i18n 时才考虑 `tool_requires` 真 gettext。

## 适用范围与查重

- **适用**：所有「头文件守卫的 gettext 回落声明 + AC_REPLACE_FUNCS 自带实现」
  模式的老 autotools 包（trueprint、同代 GNU 工具常见写法）。
- **查重**：E015/E027/E107/E123/E135 覆盖的是「链接真实 libintl（conan/系统）
  时的符号缺失/共享库找不到」，与本条「空壳头导致探测误判、双宏守卫 + 链入
  noinst 替代归档」机制不同；灰区对照 E093（musl 缺 getpass——同为
  implicit declaration/undefined reference 症状家族，但 E093 是函数在 musl 中
  纯缺失，本条是「头文件存在却为空壳」导致的 autoconf 探测误判，修复对象是
  守卫判定逻辑而非函数缺失）；grep 现有 drafts 无重叠。draft-review 相似度
  最高 0.30 以下，建议 create。
