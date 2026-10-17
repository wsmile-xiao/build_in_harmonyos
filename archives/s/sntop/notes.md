# sntop 软件级适配笔记

本目录只有一个已适配版本（`1.4.3`），全部细节写在该版本的 `notes.md`。
此处仅记录跨版本复用的判读要点。

## 上游形态

- 取源：`https://downloads.sourceforge.net/project/sntop/sntop/1.4.3/sntop-1.4.3.tar.gz`
  （`sha256 943a5af1905c3ae7ead064e531cde6e9b3dc82598bbda26ed4a43788d81d6d89`）
- 16 个文件、语言 C，`configure` + `Makefile.in` 两个手工维护的构建输入。
- `configure` 是 autoconf 2.13 的生成物但上游**不发布** `configure.ac`，
  因此不能用 autoreconf 再生成，只能按其既有形态驱动。

## 每次升版都要重看的三件事

1. `Makefile.in` 是否仍然不引用 `@CFLAGS@`/`@LDFLAGS@`。
   一旦上游补上，就该改用常规旗标注入而不再借 `-I$(INCLUDE)` 钩子。
2. `configure` 里 `AC_CHECK_LIB(ncurses, printw)` 的目标库名。
   若改为 `ncursesw` 检查，就不必再靠 `LIBS` 兜住链接。
3. `abortion()` 与各 curses 调用的 `!(flags & DAEMON)` 守卫是否仍然成立。
   这是"无 tty 也能跑一遍完整判定链路"这一消费者测试形态的前提。

## 运行时依赖

sntop 不自己发 ICMP，它 `execve("/bin/sh", {"sh","-c",cmd,0})` 调用外部探测命令。
默认命令行是 `fping -r 1 -b 24 -q <host>`，`-p` 时退化为 `ping -c 1 -s 8 -q <host>`。
部署环境需要其中之一在 PATH 中；否则程序以退出码 6 报
`sntop: error, execution of (f)ping failed`。


## 最终状态

本软件级目录当前只有一个已适配版本 `1.4.3`。该版本的构建判决、验证结论与 finish
收尾块（含时间、通过率等构建期数字）**只登记在 `1.4.3/notes.md` 的对应节**，
本文件不重复登记，以免两处数字随重跑失去同源。跨版本复用的判读要点见上面各节。
