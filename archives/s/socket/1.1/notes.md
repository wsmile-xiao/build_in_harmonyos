# socket 1.1 适配笔记

## 编译环境
- 构建系统: makefile（1992 年的 shapeTools 风格 Makefile，无 configure）
- 编译日期: 2026-09-21
- 编译器: `aarch64-unknown-linux-ohos-clang`（OHOS NDK）
- 目标: aarch64-linux-ohos
- 状态: built

## 源码来源

上游站点（`ftp.cs.tu-berlin.de`，见 README）自 1992 年起早已消失，该包在 salsa 上
也没有 VCS 仓库。Debian 归档是仍以 HTTPS 提供**未经重打包的上游原始 tarball**的权威镜像：

```
https://ftp.debian.org/debian/pool/main/s/socket/socket_1.1.orig.tar.gz
sha256 7df3eae9f23d13984f15b3b292ed1c79ca8624977c6ea46710c659a7c65ae77a
```

判定为上游原件而非 Debian 重打包的依据：文件名无 `+dfsg` 后缀、包内 18 个文件无
`debian/` 目录、`patchlevel.h` 与 CHANGES 与 1.1 发行版一致。
（`deb.debian.org` 被 PF7 拦截，`ftp.debian.org` 为仓库内既有先例。）

## 编译步骤

```bash
# 上游默认目标 all → +all，是 shapeTools 的递归包装，交叉编译下不要走它
make targets CC=aarch64-unknown-linux-ohos-clang -j1
# CFLAGS/CPPFLAGS/LDFLAGS 由 Conan 的 AutotoolsToolchain 经环境注入
```

配方中 `build()` 只调 `make targets`，编译器取自
`tools.build:compiler_executables`（R33，不依赖裸 shell 变量）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `utils.c:76: error: variable has incomplete type 'struct sigvec'` | OHOS libc 定义了 `SIG_SETMASK`，源码用 `#ifdef SIG_SETMASK` 探测「是否 BSD 信号 API」从而选中 BSD 分支，但 libc 并不提供 `struct sigvec`/`sigvec()` | `0003-utils.c.patch`：删掉 BSD 分支，统一用 POSIX `sigaction` + `sigfillset`（无平台宏分支，Linux/OHOS 行为一致） |
| 2 | `extern int errno` 在现代 libc 上不对应任何可链接符号 | errno 已是线程局部宏（`*__errno_location()`） | `0002-globals.h.patch`：改为 `#include <errno.h>` |
| 3 | 外部注入的 `-O2`/`--target` 等 flags 被整体吞掉（实测 `-O`、`-s` 覆盖） | Makefile 写死 `CC = cc` 且用 `=` 覆盖 CFLAGS/LDFLAGS；shapeTools 的 `+all` 包装又把 makefile 内的这些值以**命令行变量**形式传给子 make，命令行变量优先级最高 | `0001-Makefile.patch`：`CC ?=`、`CFLAGS ?=`、`SWITCHES` 改用 `+=` 追加；构建直接调 `targets` 目标，绕开 `+all` 递归 |
| 4 | `refresh-patch` 生成空补丁 | `init-build` 产生的 `.work` 与 `.orig` 是硬链接，原地写回的编辑器同时改掉了 `.orig`（已有草稿 E543，本次复现） | 备份修改 → 重新解包 `.orig` → `cp --remove-destination` 断链 → 重放修改后再生成补丁；`manifest.yaml` 中已记录两侧哈希 |
| 5 | qemu 下动态产物 `No such file or directory` | 缺 `/lib/ld-musl-aarch64.so.1`，x86 runner 无 OHOS sysroot（已有草稿 E544） | 功能验证一律用 `-static` 链接的副本；本机已注册 binfmt_misc，静态 aarch64 产物可直接执行 |

## 源码修改

| 补丁 | 文件 | 改动 | 含平台宏 |
|---|---|---|---|
| `0001-Makefile.patch` | `Makefile` | `CC`/`CFLAGS` 改 `?=`，`SWITCHES` 改 `+=`，尊重外部注入 | 否 |
| `0002-globals.h.patch` | `globals.h` | `extern int errno` → `#include <errno.h>` | 否 |
| `0003-utils.c.patch` | `utils.c` | BSD `sigvec()` → POSIX `sigaction()` | 否 |

三个补丁均为可移植性修复（`patch_type: portability`），不含 `__OHOS__` 等平台宏，
在 glibc/musl/OHOS 上语义一致。

## 依赖版本

无第三方依赖，仅 libc（`Dependencies` 文件为空依赖声明）。`requirements()` 为空。

## 上游测试清点（R51）

| 项 | 结果 | 证据 |
|---|---|---|
| 上游测试目录 | 无 | tarball 共 18 个文件，无 `tests/`、无 `configure` |
| 上游测试目标 | 无 | Makefile 全部 target：`all/targets/tags/TAGS/installtargets/installmanuals/doclean/subsystems/install/clean/+all/+install/+clean`；`make -n check` → `No rule to make target 'check'. Stop.` |
| 打包层测试 | 无 | Debian socket 1.1-10.1 的 `debian/` 下只有 `changelog/compat/control/copyright/patches/rules/source`，无 autopkgtest |
| 上游用例 N | 0 | — |
| 移植后可跑 N′ | 0 | 无用例可移植 |
| 补全用例 | 8 条断言 | `test_package/test_socket.py`：1 条 artifact 校验 + 7 条运行时功能断言 |

补全用例按 `socket(1)` man page 语义编写，由 Python 扮演对端做真实 TCP 交互（无 sleep 竞态），
覆盖 `socket.c` / `socketp.c` / `io.c` / `utils.c` / `siglist.c` 全部源文件与补丁 3 的信号路径。

## 验证结果

```bash
$ file /tmp/socket-testbin/socket
ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked

$ python3 test_package/test_socket.py /tmp/socket-testbin      # qemu-aarch64 + binfmt_misc 实跑
[ok] artifact: /tmp/socket-testbin/socket (aarch64 ELF, executable)
[ok] binary runs: Usage: socket [-bclqrvw] [-p prog] [-s | host] port
[ok] usage line is printed
[ok] unknown host is reported — ['socket: unknown host nosuchhost.invalid']
[ok] client mode transfers both directions — server saw b'PING\n', client stdout 'PONG'
[ok] server mode (-s) transfers both directions — client saw b'PONG\n', server stdout 'PING'
[ok] -c translates outgoing LF to CRLF — server saw b'PING\r\n'
[ok] -p wires a program to the connection — client saw b'HELLO-FROM-PROG\n'
[ok] SIGTERM runs the sigaction handler — exit status 241, stderr 'Termination signal occured, exiting'
[summary] runtime checks: 7/7 passed
```

**证据链说明（重要，勿误读为「交付产物已实跑」）**：本机是 x86_64 runner，
`conan create` 中 test_package 实际只跑了 artifact 层，**7 条运行时断言被 skip**
（脚本如实打印 `[skip] ... runtime checks SKIPPED`，不计为通过）。交付的打包产物是
动态链接 PIE（解释器 `/lib/ld-musl-aarch64.so.1`），本机无 OHOS sysroot，
拿 NDK 的 `libc.so` 当 loader 跑 `qemu-aarch64 -L` 会直接
`uncaught target signal 11`（与草稿 E544 一致）。上面的 7/7 取自**同一组 `.o`、
同一工具链**下 `-static` 重新链接的副本——源码与编译选项一致，仅链接方式不同。
真正的 aarch64 原生实跑需由 CI / 真机完成。

反向验证（防空壳测试）：把产物换成只 `print` 的假二进制 → 0/7 通过；`bindir` 为空 → 脚本 rc=1。
SIGTERM 退出码 241 = `256 + (-SIGTERM)`，与 `exitsig()` 中 `exit(-sig)` 的语义吻合，
说明补丁 3 装上的 handler 确实被调用（另在 x86 native 编译对照复现同样行为）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/socket` | aarch64-linux-ohos 可执行文件 |
| `share/man/man1/socket.1` | man page |
| `licenses/COPYRIGHT` | GPL-1.0-or-later 授权声明 |

产物含可执行文件，软件级目录已提供 `commands.json`。

## 注意事项

- 不要用上游默认的 `make`（`all` → `+all`）；shapeTools 递归会覆盖交叉编译 flags。
- `socket` 与系统无同名共享库冲突（纯可执行，不装库、不装头文件），
  `package_info()` 已清空 `includedirs`/`libdirs`。
---

**编译结束**: 2026-09-21 02:52
**最终状态**: built
