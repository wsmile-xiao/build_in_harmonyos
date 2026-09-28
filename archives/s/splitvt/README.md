# splitvt

`splitvt` 把一屏 vt100 兼容终端切成上下两个窗口，每个窗口里跑一个独立的程序：它为自己
申请两个伪终端（`/dev/ptmx` + `grantpt()/unlockpt()/ptsname()`），在两个从节点上各
`fork+exec` 一个程序，然后把两个子程序的输出重新渲染到自己终端的上半/下半屏。
上下窗口跑什么可由 `-upper/-lower` 参数或 `~/.splitvtrc` 指定；`^W` 换窗口、
`^O` 进命令模式（`q` 快速退出、`k` 杀掉当前窗口、`h` 帮助）、`^V` 引用下一个字符。

上游：<https://www.libsdl.org/projects/splitvt/>（作者 Sam Lantinga，GPL-2.0-only；
1.6.6 发布于 2006-03-11，是 splitvt 系列的最后一个版本）。

## 功能概述

- `splitvt` — 唯一的可执行命令。`-v` 打印版本，`-h` 打印用法，`-norc` 跳过启动文件，
  `-s <行数>` 设置上窗口高度，`-t <标题>` 设置 xterm 标题，`-login` 把子程序当登录 shell 跑
- `examples/splitvtrc` — 启动文件样例（`run -upper ...`、`set login on` 等指令）
- `escapes/*.codes`、`utils/` — 作者的终端转义码表与配套小工具，作参考交付

## 依赖关系

- 编译依赖：**无**（上游的 termcap 支在 `#ifdef TERMCAP` 之后；本机没有 `/usr/lib/libtermcap.a`
  让探测层打开它，未定义 TERMCAP 时 `terminal.c` 用硬编码 VT100 转义序列，功能完整）
- 运行依赖：**无第三方库** —— 产物 `DT_NEEDED` 只有 `libc.so`（由 test_package 断言，不是口头声明）
- 运行环境：stdin/stdout 必须是 tty，`TERM` 需以 `vt10` 或 `xterm` 开头（否则按文档拒绝启动），
  并需要内核提供 `/dev/ptmx` 与 `/dev/pts`

## OHOS 适配要点

- 上游 `configure` 是作者手写的 sh 脚本：编译并**运行** `config.c`，由它 `printf` 出整份 Makefile。
  它所有"特性探测"都是对 `/usr/include/xxx.h` 做 `stat` —— 本机 `/usr/include` 不存在（头文件在
  clang 的 sysroot 里）⇒ 能力宏全体静默判否；而本机 clang 同时预定义 `linux`，代码分支照旧选中
  SVR4 pty 路径。**探测层与分支层结论互相矛盾**是本包全部症状的共同根因
- 回填走 make 的 **CPPFLAGS**（上游生成的 Makefile 从不赋值它，而 make 内置 `.c` 规则会追加它）；
  **绝不覆盖 CFLAGS** —— 覆盖会连带吃掉 `-DSHELL=\"/bin/sh\"` 的两级引号转义，宏静默退化成
  `/ bin / sh` 三个 token（`use of undeclared identifier 'bin'`，DRAFT-E575 同一机制）
- `-include unistd.h` 是正确性修复：`utmp.c` 里 `ttyname()` 无原型 ⇒ aarch64 上返回指针被截成 int；
  原型可见后又暴露出 BSD 双参 `setpgrp(0,0)` 与 musl 单参 `setpgrp(void)` 的硬冲突（补丁 0001）
- sysroot 既无 `<termio.h>` 也无 `<sgtty.h>` ⇒ `misc.c`/`vttest.c` 的两条 legacy 终端分支**两头都死**，
  用 `__has_include` 能力守卫把 System V 支改接 POSIX termios（补丁 0002/0003，命中 DRAFT-E567 家族）
- 功能级修复（补丁 0005）：`dropctty()` 必须走 `setsid()` —— `ioctl(TIOCSCTTY)` 只允许会话首进程
  调用，否则子窗口永远不拥有自己的 pty，里面的 shell 只回显、不执行你敲进去的命令
- `install` 目标用 `mv` 把二进制搬进 `/usr/local/bin`（无 PREFIX/DESTDIR）⇒ 配方不调用它，
  `package()` 显式安装 `bin/splitvt`、`man/man1/splitvt.1`、`licenses/COPYING` 与 `res/splitvt/`
- 上游无任何测试套件（生成的 Makefile 只有 splitvt/clean/distclean/install/install-man 五个目标）；
  test_package 新增 2 个消费者程序 / 29 条断言，全部在**真伪终端**下驱动安装包，且每条等待都带硬超时

详细症状、根因、失败方案与适用边界见 `1.6.6/notes.md`。
