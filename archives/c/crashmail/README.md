# CrashMail II

CrashMail II 是 FidoNet 的邮件处理器（tosser/scanner）：把入站的邮件包（`*.pkt`）
投递到 `.msg` / JAM 消息区、生成出站包与 flow 文件、维护重复邮件库、统计区流量，
并提供区域订阅（AreaFix）处理。它是 Amiga 版 CrashMail 的可移植重写版本。

## 功能概述

本包交付 8 个命令行程序（`bin/`）：

| 程序 | 作用 |
| --- | --- |
| `crashmail` | 主程序：toss / scan / 打包出站 / AreaFix / settings 自检 |
| `crashwrite` | 生成入站邮件包（脚本化投递消息） |
| `crashlist` | 为 nodelist / pointlist 建立 CMNL 索引 |
| `crashgetnode` | 按 4D 地址查询节点/点位信息 |
| `crashstats` | 读取 `crashmail.stats` 并按多种维度排序输出统计 |
| `crashlistout` | 按 nodelist 变更时间输出节点清单 |
| `crashmaint` | 维护 JAM 消息库（校验/修复/重建索引） |
| `crashexport` | 把 FidoNet 包导出为可读文本 |

消息区后端支持 `*.msg`（`MSGBASE_MSG`）与 JAM（`MSGBASE_JAM`，内置 JAMLIB），
nodelist 后端支持 CMNL 与 V7+（`NODELIST_CMNL` / `NODELIST_V7P`）。

## OHOS 适配

上游为 Linux/Win32/OS2/OSX 各维护一份手写 Makefile，本包使用 `make linux`
（POSIX 实现）作为 OHOS 构建路径，未引入任何 OHOS 专属平台分支（无 `__OHOS__`
条件编译），只做可移植性修复：

- **编译器解耦**：四个 makefile 里 `CC` 被写成 `gcc $(CPPFLAGS) $(CFLAGS) ...` 的
  复合值，命令行的 `make CC=clang` 会整体替换该定义并静默丢掉 `$(DEFS)`、`-I`。
  补丁新增 `CC_BIN ?= gcc`，只重定向编译器本体，flags 仍由 makefile 自己拼装。
- **musl 头文件可见性**：`src/jamlib/mbase.c` 使用 `struct flock` / `F_SETLK` /
  `F_WRLCK` 却只 include 了 `<sys/file.h>`；glibc 的该头会传递引入 `<fcntl.h>`，
  musl 不会。改为显式 include `<fcntl.h>`。
- **`-fno-common`**：`lastt` 在 `crashmail/handle.c` 与 `crashmail/pkt.c` 里各有一份
  试探性定义，过去靠 GCC 的 `-fcommon` 静默合体；clang 15 默认 `-fno-common`，
  链接报 `duplicate symbol: lastt`。两处都改为 `static`（它们本应各自文件私有）。
- **不能 strip**：OHOS lld 会写入 `.codesign` 段，段头记录被签名镜像的长度；
  链接完成后对该范围内的任何字节修改都会让签名校验失败，内核以
  `Operation not permitted`（退出码 126）拒绝 exec。`strip` / `llvm-strip` /
  `objcopy` 因此都不能用于 OHOS 产物，配方以 `STRIP=:` 关闭上游的 strip 步骤。
- **`/bin/bash` 不存在**：上游 `tests/roundup` 的 shebang 是 `#!/bin/bash`。
  OHOS 只提供 `/data/service/hnp/bin/bash`，因此用 PATH / `CONFIG_SHELL`
  解析出的 bash 显式启动同一套件，未改动任何用例内容。
- **toybox mktemp 要求 6 个 X**：`tests/roundup` 用 `mktemp -d -t .roundup.XXX`
  建临时目录，而 GNU coreutils 接受 ≥3 个 X、toybox 要求恰好 6 个。设备上
  PATH 命中的是 coreutils mktemp（本地全绿），CI worker 上没有它、落到 toybox
  即报 `mktemp: need XXXXXX: Not supported` 并返回 1，整个套件一条用例都跑不到。
  补丁 `0008-tests-roundup.patch` 把模板加宽为 `.roundup.XXXXXX`（单 token 改动）。
  这是"设备全绿 ≠ CI 绿"的又一实例，与 CI worker 的 meson/PATH 差异同族。

安全属性无需额外 flags：OHOS clang 15 / lld 的默认输出已是 PIE（`Type: DYN`）
并带 `GNU_RELRO`、`BIND_NOW`、`GNU_STACK RW`（NX）。

## 依赖关系

- 编译依赖：无（仅 libc/POSIX；内置 JAMLIB 静态编入）
- 运行依赖：无（8 个可执行文件仅 `DT_NEEDED libc.so`）
- JAMLIB 以 LGPL-2.1-or-later 分发，许可证文本随包安装到 `licenses/LICENSE`

## 参考资料

- 上游主页：<http://ftnapps.sourceforge.net/crashmail.html>
- 上游代码：<http://sourceforge.net/p/ftnapps/crashmail/code/>
- 发行文件：<http://sourceforge.net/projects/crashmail.ftnapps.p/files/1.7/>
- 配置关键字文档：源码 `doc/example.prefs`（随包安装到 `share/doc/crashmail/`）
- man 手册：随包安装到 `share/man/man1/`
