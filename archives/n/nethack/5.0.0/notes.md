# NetHack 5.0.0 适配笔记

## 软件信息
- 名称: nethack
- 版本: 5.0.0
- 上游: https://www.nethack.org/（Release Notes: https://nethack.org/v500/release.html，2026-05-02 发布）
- 源码: https://www.nethack.org/download/5.0.0/nethack-500-src.tgz（sha256 2959b7886aac76185b90aea0c9f80d14343f604de0ae96b3dd2a760f7ab3bde9）
- 构建系统: 纯 Makefile（sys/unix/setup.sh 根据 hints/*.500 生成 Makefile）
- 产物: nethack 终端游戏 + dat 游戏数据（含 DLB nhdat）+ recover 工具

## 与 3.6.7 的差异
- 源码符合 C99；移除跨平台构建障碍（官方称 cross-compiling 支持，见顶层 Cross-compiling 文件）。
- 构建时 yacc/lex 关卡编译器、地牢编译器、makedefs 任务文本处理被 Lua 文本替代，运行时由游戏加载处理；因此新增对 Lua 5.4.8 的硬依赖（Makefile.top LUA_VERSION=5.4.8）。
- hints 文件升级为 500 系列模块化结构（WHICH_OS + HINTSVERSION 500 + #-INCLUDE 组装），旧式全手写 hints 不再适用。
- dat 关卡源变为 *.lua；test/ 新增 9 个 Lua 测试文件，但均为 wizmode 手工用例，无自动化 harness。

## OHOS 适配要点
1. hints 派生自上游 sys/unix/hints/linux.500：保留全部 #-INCLUDE（multiw/compiler/misc/cross/gbdates/multisnd/response 等），在 multiw-2.500 求值前强制 WANT_WIN_TTY=1、WANT_WIN_CURSES=1、WANT_DEFAULT=curses；make 命令行再传一次三者，双保险。
2. curses 链接仓库 ncurses/6.6（ncursesw 宽字符静态库）：POST 覆盖 CURSESLIB=-L<conan> -lncursesw，NCURSES_CFLAGS 注入 -I<conan>，避免依赖系统 ncurses/tinfo 与 pkg-config。
3. Lua 使用仓库 lua/5.4.8 作 system Lua：hints POST 纠正变量名（TOPLUALIB/LUALIB/LUALIBS/LUAHEADERS/LUATOP，而非误写的 LUATOPLIB 置空），TOPLUALIB/LUALIB 指向 conan 的 liblua 归档；setup.sh 之后 _patch_system_lua() 预生成 include/nhlua.h（绝对路径 include，不带 ../ 前缀）并将顶层 Makefile 的 include/nhlua.h 先决条件与 bundled lib/lua-*.a 规则打桩，彻底跳过内嵌 lib/lua 构建与 `make fetch-lua` 的网络下载；CFLAGS/LFLAGS 追加依赖的 -I/-L。
4. CFLAGS/LFLAGS 追加全部依赖的 -I/-L；CC/CXX 取自 tools.build:compiler_executables，经 make 命令行传入，覆盖子构建硬编码。
5. CHOWN/CHGRP 置为 true，跳过 setuid/setgid 安装逻辑；PREFIX=/usr，HACKDIR/SHELLDIR/INSTDIR/VARDIR 定向到 /usr/bin 与 /usr/share/nethack。
6. 上游 make install 不支持 DESTDIR 且会 rm -rf HACKDIR，配方改为手动打包：src/nethack + util/recover -> bin/，dat/* + sys/unix/sysconf -> share/nethack/，license -> licenses/。
7. OHOS 无 glibc execinfo.h/backtrace 且无 xdg-open/gdb，而 config.h 在 __linux__ 下默认启用 CRASHREPORT+PANICTRACE，导致 report.c 的 backtrace/backtrace_symbols 编译失败；hints POST 追加 -DNOCRASHREPORT -DNOPANICTRACE 关闭崩溃上报栈回溯（纯平台能力缺失的构建修复，不涉及测试口径）。

## 上游测试审计（结论：无自动化套件）
- 源码分发 Files 清单含 test/ 9 文件：README.md、test_cnf.lua、test_des.lua、test_lev.lua、test_obj.lua、test_sel.lua、test_shk.lua、test_src.lua、testmove.lua、testwish.lua。
- test/README.md 用法：先无 DLB 编译安装，把 lua 拷入 playground，以 wizmode 启动，用 wizloadlua 扩展命令逐个手工加载运行。无 plan/断言计数、无退出码 harness、无 `make check` 集成，退出码 0 不代表用例执行。
- sys/libnh/test（README.md、libtest.c、run.sh）仅服务 WANT_LIBNH/libnethack.a 与 wasm/nethack.js（run.sh lib/runlib/wasm/runwasm/bin），默认 tty/curses 构建不编译不运行。
- 顶层与 sys/unix/Makefile.* 无 check/test/ctest 目标；sys/unix/Makefile.check 仅校验生成 Makefile 是否过期（checkmakefiles），不运行用例。
- 全树无 TEST/TEST_F（gtest）、def test_（pytest）、TESTS/check_PROGRAMS（automake）、ctest 注册。`make -n check` 无规则（No rule to make target 'check'），执行 0 用例。
- 因此 test_package/MANIFEST.yml 记 upstream_tests_exist: false，并附完整审计；真机输出 HMBS_UPSTREAM_TEST_RESULT status:"no_tests"、discovered/executed 0。

## 测试
- test_package/test.sh（sh）：断言 1) `nethack --version` 输出匹配 `NetHack.*5\.0\.0`（上游 version_id 格式为 `Unix NetHack Version 5.0.0 - last build ...`，含 `Version` 一词，旧模式 `NetHack 5.0.0` 永不命中）；断言 2) `nethack --showpaths` 退出 0 且输出非空。先落盘再 grep/cat，避免 `| tee | grep` 在无 pipefail 的 /bin/sh 下掩盖二进制退出码；HOME 缺失或只读时回退到 TMPDIR。
- test_package/conanfile.py 经 CONFIG_SHELL 的 shell 以 `NETHACKDIR=<pkg>/share/nethack` 执行 test.sh（配方编译期 HACKDIR=/usr/share/nethack，真机不存在该目录；--version 在 chdir 前退出不受影响，--showpaths 经 chdirx(dir, TRUE) 必须指向打包 playground），成功后打印 HMBS_TEST_PACKAGE_RESULT（discovered=2/passedCount=2）与 HMBS_UPSTREAM_TEST_RESULT（no_tests/0），失败抛 ConanException。
- 证伪说明：版本断言为落盘后 grep（空即非零退出），--showpaths 要求退出 0 且输出非空（test -s）并 cat 留证；两者均无 plan 跳过逻辑，不存在静默跳过。

## 依赖
- ncurses/6.6（仓库内已有适配，wide-char 静态库）
- lua/5.4.8（仓库内已有适配，与 NetHack 5.0 所需版本一致）
