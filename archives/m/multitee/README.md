# multitee

> **多路 tee**：把一个或多个输入文件描述符的数据同时发送到多个输出描述符。
> Daniel J. Bernstein 1991 年发布，public domain。

## 简介

`multitee` 的参数形如 `fdin-fdout,fdout,...`，含义是把描述符 `fdin` 上读到的全部数据写到每个 `fdout`。
参数可以给多个，从而把多路输入合并到同一输出。常见用法：

- `multitee 0-1,4,5 4>foo 5>bar` 等价于 `tee foo bar`，但阻塞行为更好；
- `multitee 0:1 3:1` 把 stdin 和 fd 3 合并输出到 stdout。

输出端写成 `:fd` 时，遇到 SIGPIPE 直接退出；写成 `-fd` / `,fd` 时，写错误只打印告警，并放弃这个输出。
`efd` 表示输入端到达 EOF 时，把 `fd` 也视为 EOF。选项 `-b size` 设置输入缓冲大小（默认 8192），`-q` 静默，`-v` 详细输出。

## OHOS 适配要点

- 上游只以 shar 发布，没有构建文件。补丁 0001 新增一个最小 Makefile，编译器和标志来自 Conan 的 AutotoolsToolchain。
- `sigdfl.c` / `sigsched.c` 使用 4.2BSD 信号接口 `sigvec`/`sigblock`/`sigsetmask`/`sigmask`，OHOS musl 不提供这些接口。
  补丁 0004/0005 将其改写为 POSIX `sigaction`/`sigprocmask`/`sigset_t`，没有加平台宏。
- 补丁 0002/0003 补上标准头原型（LP64），并去掉与 libc 冲突的前 ANSI `malloc`/`free` 声明。
- 只交付 `bin/multitee` 和 `share/man/man1/multitee.1`。上游附带的 `tee.c` 克隆不构建，避免遮蔽系统 `tee`。
- 上游没有测试。`test_package` 补全了测试：4 项制品检查（aarch64 PIE、OHOS musl 解释器等），以及复制、扇出、
  合并、EOF 联动、EPIPE/SIGPIPE、`-b`/`-q`、错误选项等 11 项功能用例。

## 依赖

无（仅 libc）。

## 参考

- [源码仓库（Debian 托管，upstream/3.0 为原始发布导入）](https://salsa.debian.org/debian/multitee)
- [作者原始发布（alt.sources shar）](https://cr.yp.to/software/multitee-3.0.shar.gz)
