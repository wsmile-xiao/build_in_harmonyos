# E583: 老项目 AC_CHECK_LIB(curses) 在 OHOS 需改 ncursesw（宽字符版）

## 错误特征

- `checking for main in -lcurses... no`
- 链接失败：`undefined reference to 'tgetent'/'tgetstr'/'tgoto'/'setupterm'`
- `term.h file not found`（头文件路径正确但库名不匹配）

## 触发条件

1. 2003 年代老 autotools 项目，configure.in 用 `AC_CHECK_LIB(curses, main)` 检测
2. OHOS conan 制品仓 ncurses/6.5 包只提供宽字符版 `libncursesw.a`（含 termcap API），不提供 `libcurses.a`
3. 项目实际只用 `<term.h>` 的 termcap 函数（tgetent/tgetstr/tgoto/setupterm 等）

## 根因

conan 鸿蒙 ncurses 包为宽字符构建，产物为 libncursesw.a（+ libformw/menuw/panelw），无 libcurses 兼容名。老项目 `AC_CHECK_LIB(curses, main)` 在 OHOS 上检测返回 no，LIBS 不含 -lcurses；随后源码调用 termcap 函数（符号在 libncursesw.a）链接失败。

## 解决方案

将 configure.in 与 configure 两处 `AC_CHECK_LIB(curses, main)` 改为 `AC_CHECK_LIB(ncursesw, main)`：

```sh
# configure.in 源头（优先级①）
sed -i 's/AC_CHECK_LIB(curses, main)/AC_CHECK_LIB(ncursesw, main)/' configure.in
# configure 生成文件同步（优先级②）
sed -i 's/checking for main in -lcurses/checking for main in -lncursesw/; s/ac_cv_lib_curses_main/ac_cv_lib_ncursesw_main/g; s/LIBS="-lcurses  \$LIBS"/LIBS="-lncursesw  $LIBS"/; s/LIBS="-lcurses \$LIBS"/LIBS="-lncursesw $LIBS"/' configure
```

修复后 LIBS 变为 `-ldl -lncursesw -lutil`，termcap API 全部解析。

## 验证证据

- zhcon 0.2.6 修复后：`checking for main in -lncursesw... yes`、`#define HAVE_LIBCURSES 1`（宏名沿用不影响）
- 链接成功，`zhcon --version` 可运行
- conan-verify G2 conan create 干净构建通过

## 适用边界

- 适用：老 autotools 项目 + conan ncurses（宽字符版）+ termcap/terminfo API 使用
- 不适用：上游硬编码 `-lcurses` 且无法改检测的场景（此时应在私有 build prefix 建 libcurses 符号链接，不污染系统路径）
- 注意：源码中 curses API（initscr/wgetch 等）同样在 libncursesw.a，改库名后兼容

## 关联条目

- similar_to: E568（ncurses terminfo 路径问题，不同根因——E568 是运行时找不到 terminfo 数据，E583 是编译期库检测失败）
