# E582: gettext AM_GNU_GETTEXT conftest 64 位指针截断，libintl 检测误判

## 错误特征

- `conftest.cc:92:8: error: cast from pointer to smaller type 'int' loses information`
- `return (int) gettext ("") + _nl_msg_cat_cntr + *_nl_expand_alias (0)`
- `error: no matching function for call to '_nl_expand_alias'`（新版 libintl.h 为无参原型）
- `checking for GNU gettext in libintl... no` → `where the gettext function comes from... included intl directory`
- 链接阶段 `undefined symbol: g_libintl_gettext / libintl_gettext / libintl_bindtextdomain / libintl_textdomain`

## 触发条件

1. 老版本 autoconf + gettext 宏（AM_GNU_GETTEXT）生成的 configure
2. 64 位平台（aarch64）编译 conftest
3. 系统中存在新版 libintl.h（原型更严格）
4. 源码 tarball 不携带 intl/ 目录（回退 included intl 后无可链接目标）

## 根因

AM_GNU_GETTEXT 的 conftest 测试程序 `return (int) gettext("") + ... + *_nl_expand_alias(0)` 在 64 位下有双重问题：① 指针转 int 截断（clang 严格报错）；② `_nl_expand_alias` 以 1 个参数调用但新版 libintl.h 原型为无参。conftest 编译失败 → configure 误判系统 libintl 不可用 → 回退 "included intl directory"（引用 `${top_builddir}/intl/libintl.a`）。若 tarball 无 intl/ 目录，链接报 g_libintl_* 未定义。

## 解决方案

修改 configure 脚本中 conftest 的调用（两处）：

```sh
# (int) gettext("") → (int)(long) gettext("")   （先经 64 位 long 再截断）
# _nl_expand_alias(0) → _nl_expand_alias()       （无参调用）
sed -i 's|return (int) gettext ("").*|return (int) (long) gettext ("") + _nl_msg_cat_cntr + *_nl_expand_alias ()|g' configure
```

修复后 `GNU gettext in libintl... yes`，configure 走外部 libintl 路径（`USE_INCLUDED_LIBINTL=no`、`LIBINTL=-lintl`）。

## 验证证据

- zhcon 0.2.6 修复后：`checking for GNU gettext in libintl... yes`、`where the gettext function comes from... external libintl`
- Makefile 中 `USE_INCLUDED_LIBINTL = no`、`LIBINTL = -lintl`
- conan-verify G2 conan create 干净构建通过

## 适用边界

- 适用：AM_GNU_GETTEXT 老宏 + 64 位平台 + 新版 libintl 头
- 不适用：系统 libintl 头为旧版（无严格原型）时 conftest 可能可编译通过
- 注意：若 usr/local 的 libintl.h 是 GLib proxy 头（`#define gettext g_libintl_gettext`）而 libintl.so 导出的是 `libintl_gettext` 标准名，属头库符号不匹配，应改用 conan 制品仓 gettext 标准头库，而非继续修补 conftest

## 关联条目

- similar_to: E566（gettext/编译标志相关）、E571（install 规则 DESTDIR）
- 区别：E582 聚焦 gettext 检测 conftest 自身的 64 位兼容，E566 聚焦 PkgConfigDeps 提取 .pc flags
