# DRAFT-6053-lgeneral-1.4.4-bundled-gettext-0.10-ac29-subst-loss — gettext 0.10.x 内嵌 intl 与 autoconf 2.69 再生 configure 组合断裂

- 触发事件：lgeneral 1.4.4 适配，intl 目录 make 失败 + LC_MESSAGES 编译错误
- 路径：Path B（知识库扩展）
- 编号：DRAFT-6053

## 现象

OHOS (musl) 上构建内嵌 gettext 0.10.35 intl/ 目录的老项目（lgeneral
1.4.4，1999 年代代码、configure 已被 autoconf 2.69 再生）时，按顺序爆出
五种错误：

1. `make: No rule to make target 'libintl.@l@a', needed by 'all-yes'`
2. `make: No rule to make target 'intlh.inst', needed by 'all-yes'`
3. `error: use of undeclared identifier 'LC_MESSAGES'`（intl/dgettext.c、
   intl/libgettext.h）
4. 运行期 `implicit declaration of function 'dcgettext__'` 崩溃
   （util/localize.h 包含了 OHOS sysroot 的空壳 <libintl.h>）
5. `make check` 链接 check_PROGRAMS 报 `undefined symbol: dcgettext__`

## 根因（对照实验实证）

glibc 发行版从不触发：系统有 gettext → configure 判
`USE_INCLUDED_LIBINTL=no` → intl/ 走 all-no 目标，整个目录不构建。
musl/OHOS 无系统 gettext → `USE_INCLUDED_LIBINTL=yes` → 三处历史断裂
同时显形：

| # | 断裂点 | 机制 |
|---|--------|------|
| 1 | `l = @l@` 不被替换 | gettext 0.10.35 用单字母变量 `l`（INTL_LIBTOOL_SUFFIX_PREFIX 的展开载体）表示 libtool 后缀；autoconf 2.13 的 sed 全表替换会把它换成空；**2.69 的 config.status 只替换 ac_subst_vars 里登记过的变量**，`l` 不在表内 → `libintl.$la` 展开成字面 `libintl.@l@a`。实证：两棵独立构建树生成的 intl/Makefile 第 44 行均为 `l = @l@`，而 config.status 里 `S["INTL_LIBTOOL_SUFFIX_PREFIX"]=""` 存在——替换链断裂在 `l` 这一环 |
| 2 | `HAVE_LOCALE_H` 未定义 | 旧 AM_GNU_GETTEXT 的探测宏没有进入 2.69 再生的 configure → `#ifdef HAVE_LOCALE_H` 恒假 → 不含 <locale.h> → musl 上 LC_MESSAGES 取不到（musl 的 locale.h 存在且定义了它，只是没被包含） |
| 3 | `intlh.inst` 目标缺失 | tarball 未随附 intl/intlh.inst.in 模板（外置 gettext 用户才需要），但 all-yes 仍引用 |
| 4 | sysroot <libintl.h> 空壳 | OHOS 的 libintl.h 无任何 gettext 原型；包含它等于什么都没声明 → dcgettext__ 隐式声明 → 运行时崩 |
| 5 | check_PROGRAMS 缺 $(INTLLIBS) | 上游 testfile_LDADD 只写业务静态库；glibc 上 dcgettext__ 在 libc 里所以从未显形，musl 上必须显式链 intl |

## 可复用处置（intl 定点补丁五件套）

全部只动 intl/ 辅助文件与链接变量，不碰业务代码：

```diff
# 1) intl/Makefile.in —— 空后缀 + 移除 intlh.inst
-l = @l@
+l =
-all-yes: libintl.$la intlh.inst
+all-yes: libintl.$la

# 2) intl/dgettext.c / intl/libgettext.h —— 无条件包含
-#ifdef HAVE_LOCALE_H
-# include <locale.h>
-#endif
+#include <locale.h>

# 3) util/localize.h —— 绕开 sysroot 空壳，用内嵌头
-#include <libintl.h>
+#include "intl/libgettext.h"

# 4) src/Makefile.am / Makefile.in —— 恢复上游测试
-testfile_LDADD = $(top_builddir)/util/libutil.a
+testfile_LDADD = $(top_builddir)/util/libutil.a $(INTLLIBS)

# 5) configure —— HMDFS 上 umask 子壳失败（E112/E206 同族，configure 侧变体）
-  { test ! -f tmp/conftest.cs || ... (umask 077 && mktemp ...) }
+  去掉 umask 077 子壳
```

注意：
- 补丁必须用 edit_file 或 `patch -p1` 真实落地并回验——toybox patch 对
  上下文行**前导空格缺失**会静默跳过 hunk（本 session 实测：手写补丁
  6 个只有 1 个真正生效）；
- `intl/libgettext.h` 与 sysroot `libintl.h` 的 include guard 同名
  （`_LIBINTL_H`），两条包含路径同时存在会冲突，必须保证只走内嵌一条。

## 边界与判断

- 只适用于"内嵌 gettext 0.10.x intl/ + configure 被新 autoconf 再生"的
  组合；gettext 0.11+ 换了机制（gt_LIBTOOL），没有 @l@ 问题；
- 若项目没有 intl/ 目录、直接用系统 gettext，走 E015（补 -lintl）或
  `--disable-nls`，不是本模式；
- `USE_INCLUDED_LIBINTL=no` 的 glibc 环境上这些补丁全部空转无害——
  判断是否套用的第一步永远是查 configure 结果里这个变量的值。

## 实证

- lgeneral 1.4.4（feat/lgeneral-1.4.4 分支）：
  - 修复前：make 在 intl/ 即失败（错误 1/2），跨过后面还有错误 3/4/5；
  - 修复后：干净树（verify4/verify5）`make -j1` rc=0、`make check` 构建并
    运行 testfile（列目录正确、缺失目录 rc=1）、`make install` rc=0；
  - conan create 全流程通过，test_package 12 项检查（CLI ×5、干净失败
    ×1、ELF ×4、testfile ×2）全过；
  - 补丁：archives/l/lgeneral/1.4.4/patches/0001–0007；
  - 日志：~/lg/make5.log、~/lg/check3.log、~/lg/conan-create5.log。
