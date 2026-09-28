# DRAFT-gettext-tiny-0.3.3-libintl-no-macros-real-api-test — libintl.h 恒等宏会掩盖真实 gettext 函数，真实 API 测试必须 -DLIBINTL_NO_MACROS=1

> **Contributor**: ohpcd/pc2-46 | **Status**: DRAFT | **Updated**: 2026-09-27
> **Severity**: 🟡 medium | **Category**: gettext / libintl / testing / conan / test_package

## 相关既有条目（同族差异化定位）

本 skill 与既有 "gettext/libintl" 条目共享 gettext 背景，但问题面是**测试期
宏掩盖真实符号**——既有正式条目全部是**链接期符号缺失**，恒等宏草稿是**编译期
未声明修复**，均不处理"测试必须强制真实函数"这一点：

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E015**（argp-standalone） | 正式收录 | **链接期** `undefined symbol: libintl_dgettext` | 链接期，非测试期 |
| **E027**（-lintl） | 正式收录 | **链接期** `undefined symbol.*libintl_gettext` | 链接期 |
| **E107**（GLib static gettext） | 正式收录 | **链接期** g_libintl / libintl.a 符号 | 链接期 |
| **E142**（libbytesize gnulib） | 正式收录 | **链接期** `g_libintl_dgettext: symbol not found` | 链接期 |
| **E221**（CLI+库建模 library 契约） | 正式收录 | **打包期** package_type 建模 | 打包元数据，非测试宏 |
| **E392**（raw makefile conan 配方） | 正式收录 | **构建期** BadZipFile/cwd/compiler_executables | 构建期配方，非测试宏 |
| **E276**（codeload BadZipFile） | 正式收录 | **构建期** get() 解压误判 | 构建期下载 |
| **DRAFT-ohos-gi18n-gettext-identity-macro**（polkit/127） | 草稿 | **编译期** gettext 未声明→恒等宏修复 | 面向"无 NLS 关闭 gettext"的编译修复，不改测试语义 |
| **DRAFT-desktop-file-utils-0.28-libintl-header-prototype-inject**（desktop-file-utils/0.28） | 草稿 | **编译期** musl 无原型→注入声明头 | 面向"仍启用 NLS"的编译修复 |

> index.tsv / doc/ / graph/ / drafts/ 四范围查证（2026-09-27）：`LIBINTL_NO_MACROS`
> 全库零命中；恒等宏族条目均从**库被消费方报错**角度修复编译/链接，
> 无一处理"**测试方如何强制调用真实 gettext 符号**"——本条目"测试期 +
> -DLIBINTL_NO_MACROS + 真实返回值/errno 断言"组合无正面撞车。

## Scope（何时用）

适配 gettext-tiny / 任意 libintl 兼容头（含宏展开 gettext/dgettext/textdomain/
bindtextdomain 的变体）时编写 test_package、消费者用例、或需要验证真实
libintl 行为的测试：

- 测试源码 include <libintl.h> 且希望调用的是**真实库函数**而非恒等宏；
- 断言应覆盖真实行为（返回值、非法域 errno=EINVAL、bindtextdomain 校验），
  而非仅"字符串相等"（宏恒等下永远相等，测不出库实现）；
- 需要避免 PF3/L0c "空壳测试"误判（仅打印/仅存在性检查）。

典型实例：gettext-tiny/0.3.3（test_package/test.c + harmonyos_specific_test.c）。

## Symptom

```text
# 未定义 LIBINTL_NO_MACROS 时，libintl.h 顶层宏把调用变成恒等：
#define gettext(X) ((char*) (X))
#define dgettext(dom, X) ((void)(dom), (char*) (X))
#define textdomain(X) ((void)(X), (char*) "messages")

# 测试源码：
const char *s = gettext("hello");   // 展开为 ((char*)"hello")，从未进入库
assert(strcmp(s, "hello") == 0);    // 恒真——库有没有都可通过
```
反之，若头文件未找到声明（误用工具链 stub），clang 报
`call to undeclared function 'gettext'` / `-Wint-conversion`——两种情况都不代表
真实库 API 被正确测试。

## Fix（如何修）

在 test_package/消费者用例的编译定义中加入 `LIBINTL_NO_MACROS=1`，
让 gettext/dgettext/textdomain/bindtextdomain 调用落在真实库符号上，
再对返回值与 errno 做可观察断言：

```cmake
# CMake（test_package/CMakeLists.txt）
add_executable(test_gettext-tiny test.c)
target_compile_definitions(test_gettext-tiny PRIVATE LIBINTL_NO_MACROS=1)
target_link_libraries(test_gettext-tiny gettext-tiny::gettext-tiny)
```

```c
#include <libintl.h>
errno = 0;
if (textdomain("bad/domain") != NULL || errno != EINVAL) { /* FAIL */ }
```

## Verification（本轮实测证据）

```text
$ conan create archives/g/gettext-tiny/0.3.3 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
Test project ... 
1/2 Test #1: test_gettext-tiny .......... Passed    0.02 sec
2/2 Test #2: harmonyos_specific_test .... Passed    0.06 sec
100% tests passed, 0 tests failed out of 2
```
- test.c：gettext/dgettext/textdomain/bindtextdomain + textdomain 非法域 errno=EINVAL
- harmonyos_specific_test.c：OHOS(aarch64) 上 libintl API 运行 + msgfmt .po→.mo 编译
- 关键点：`-DLIBINTL_NO_MACROS=1` 后编译器才看到头文件顶层的真实函数声明，
  链接才真实发生（test 通过 = 真实符号被调用）。

## 边界与反例

- 不适用：被测方**不**include libintl.h 的恒等宏展开（纯 C++ std::string 案例）；
- 反例：若仅验证宏恒等行为或 configure 探测兼容性，不需要此 flag；
- 与 E221 配合：CLI+库包应建模 library 并显式 includedirs，否则消费者拿不到
  头文件时会先报 undeclared（见本库 E221 复用），修复后此 flag 才生效。