# ldapvi 1.8 适配笔记

## 任务身份
- 平台：ldapvi 1.8，Issue #2194（积分赛），分支 feat/ldapvi-1.8
- 上游：ldapvi by David Lichteblau，http://www.lichteblau.com/ldapvi/，
  tarball http://www.lichteblau.com/download/ldapvi-1.8.tar.gz（GPL-2.0，autotools）
- 归档：archives/l/ldapvi/1.8，conan ref ldapvi/1.8（application，命令工具）

## 依赖与供给（W0/R36 先例：abook/adcli）
- ncurses/6.4：已发布到 ohpcd，conan requires 静态宽字符（含 term.h/curses.h）
- openldap 2.6.7、readline 8.2、popt 1.16、glib 2.88.0、pcre2 10.40、
  openssl 3.5.6：未发布到 ohpcd，按 abook/adcli 先例在 generate() 从
  cmd-pkgs 预编译包供给到 SYS_PREFIX（~/usr/local），并把 .pc prefix 归一到 SYS_PREFIX
- glib 需要 pcre2（glib-2.0.pc Requires libpcre2-8）

## 探索构建确认的问题与修复（补丁）
1. configure umask 077 → 022（E114/E011，HMDFS 临时目录权限）→ 0001
2. test1/test2 链接行缺 $(LDFLAGS)（测试无法链接 -L 前缀）→ 0002
3. open_memstream/tmpfile/fmemopen 符号存在但运行时不可用（E302/E320，
   fclose EBADF、流内容不发布）→ test_print.c/test_search.c/test_diff.c/
   test_parse.c/test_parseldif.c 改用 mkstemp/fopen 命名临时文件，
   断言/数据/预期均不变 → 0003-0007
4. /tmp 只读（E002）→ test_arguments.c mkdtemp 模板、test_parse.c file://
   路径改用相对路径 → 0008
5. ARM64 AAPCS64 下 char 默认 unsigned，而上游测试假定 signed char
   （print_mode_ascii 期望 0xC3 0xA9 判为非可读→base64）→
   configure CFLAGS=-fsigned-char（构建参数，非源码修改）
6. tigetstr 在 libncursesw（configure 只搜 -lcurses/-lncurses）→
   configure LIBS=-lncursesw

## 上游测试
- 入口：make test → test1（test_main.c 驱动，parseldif/diff/parse/print/
  data/schema/arguments 套件）+ test2（test_search.c）
- 结果（探索构建 + 干净源码打补丁后均复现）：test1 247 passed / 0 failed，
  test2 17 passed / 0 failed，合计 264/264，无 skip/error/timeout
- 修改的上游测试文件：test_print.c、test_search.c、test_diff.c、
  test_parse.c、test_parseldif.c、test_arguments.c —— 仅替换运行时不可用
  的 libc 内存流/tmpfile 机制与 /tmp 路径，断言、数据、用例选择、
  skip 条件与预期全部不变（逐文件说明见 conandata.yml patch_description）

## 消费者测试
- test_package：C 程序调用 ldapvi --version / --help，验证二进制可执行，
  2 断言（真实命令执行，非空壳）

## 关键命令与退出码（探索构建）
- ./configure --prefix=/ LIBS="-lncursesw" CFLAGS="-fsigned-char" → 0
- make -j1 → 0
- make test -j1 → 0（264/264）
- ./ldapvi --version → "ldapvi 1.8"，退出 0
- ./ldapvi --help → Usage，退出 0
---

**编译结束**: 2026-08-16 17:26
**最终状态**: built
