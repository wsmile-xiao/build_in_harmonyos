# sash

sash（Stand-alone shell）是 David I. Bell 编写的**系统救援用独立 shell**：它把
一大批标准命令以「内建命令」的形式实现在同一个可执行文件里，目的是在共享库或
外部可执行文件缺失、系统起不来的时候，仍然有一个能干活的环境把系统救回来。

## 功能概述

- **内建命令命名带前导 `-`**（如 `-cp` `-mv` `-rm` `-gzip` `-tar` `-ar` `-ls`
  `-find` `-grep` `-dd` `-ed` `-chown` `-chgrp` `-chmod` `-ln` `-mkdir`
  `-mknod` `-cmp` `-file` `-kill` `-losetup` `-mount` `-umount` `-pivot_root`
  `-chroot` `-chattr` `-lsattr`）。带前导 `-` 是为了与同名外部命令区分，
  让内建实现优先被显式调用。
- 另有一批不带前缀的 shell 内建：`alias` `aliasall` `cd` `exec` `exit`
  `help` `prompt` `set` `umask` `unalias` `unset` 等。
- 可作为普通 shell 使用：`sash -c '<命令>'` 执行单条命令、`sash -f <脚本>`
  执行脚本文件、`sash -a` 把内建命令别名到标准命令名上。
- 命令行选项解析、内建命令表分派、以及 `-gzip`/`-gunzip` 的压缩路径都实现在包
  内，不依赖外部程序；`-tar` 只做归档不含压缩路径（`cmd_tar.c` 对 gz*/compress/popen/system( 命中 0）。
- 上游形态是裸 GNU Makefile 工程（没有 configure / CMake / meson），
  13 个 `.c`、单目录、无子模块。

## OHOS 适配

- **构建系统**：裸 Makefile。配方不覆盖上游 `CFLAGS` 赋值（其中携带全部
  `-DHAVE_*` 特性开关与 `-Wall -Wmissing-prototypes`），改为只用 make 命令行
  覆盖 `LDFLAGS` 并注入 `CPPFLAGS`（依赖头路径），因此上游的告警面与特性
  宏定义一字不动地保留。
- **链接方式**：上游 `LDFLAGS = -static` 覆盖为动态链基础运行时。本包唯一
  外部依赖 zlib 在制品仓的 OHOS 包里只提供 `libz.a`（R26 系统同名库强制
  静态），故 zlib 仍以静态方式吃入，不新增运行时 `.so` 依赖 —— 与上游
  "救援 shell 不额外拖运行时依赖" 的意图保持一致。
- **`-chattr` / `-lsattr` 已关闭**：上游 `cmd_chattr.c` 的整个文件体由
  `#if HAVE_LINUX_ATTR` 包住，内部 `#include <ext2fs/ext2_fs.h>`；HarmonyOS
  PC 的 native SDK sysroot 不提供 `ext2fs/ext2_fs.h`。适配取上游自带的
  `HAVE_LINUX_ATTR` 开关置 0，即从命令表移除这两条内建。这是**功能面裁剪**
  （ext2 私有属性位，非通用 POSIX 能力），不是上游不支持。
- **`MOUNT_TYPE` 传参修正**：上游把该宏写成 `'"ext3"'`，经 shell 引号剥离后
  实际到达编译器时丢掉了字符串引号，会使 `cmds.c` 的 `type = MOUNT_TYPE;`
  编译失败；适配改为传字面转义形态，宏值语义与上游默认值（字符串 `"ext3"`）
  完全一致。
- **安装布局**：上游 `install` 规则把 `BINDIR` 写死 `/bin`、`MANDIR` 写死
  `/usr/man`（并非 `/usr/share/man`）且使用裸 `cp`。配方不调用 `make install`，
  改在打包阶段按 Conan 布局落 `bin/sash` 与 `share/man/man1/sash.1`。
- **运行级限制（重要，非适配缺陷）**：sash 的一批内建命令是特权操作 ——
  `-mount` / `-umount` / `-chroot` / `-pivot_root` / `-losetup` / `-mknod`
  需要 root 与 `CAP_SYS_ADMIN`，`-kill` 需要信号权限。HarmonyOS PC 上普通
  应用运行在受限非 root 沙箱内，这些命令在该环境下必然受限；它们**编译面
  正常通过**（所需头与 syscall 声明在 SDK sysroot 内齐备），属于运行级环境
  限制。上游测试总数为 0，因此该限制不减少任何可执行测试分母（见
  `3.8/test_package/MANIFEST.yml` 的清点证据）。

## 依赖关系

- **运行/编译依赖**：zlib（Makefile `LIBS = -lz`，供 `-gzip` / `-gunzip`
  内建命令）。实测调用面为 zlib 的高层 `gz*` 接口：`gzopen` / `gzwrite` /
  `gzread` / `gzclose` / `gzerror`（实测 16 处命中全部位于 `cmd_gzip.c`，`cmd_tar.c` 命中 0），不使用
  `deflate*` / `inflate*` 底层接口。配方里对应 `zlib/1.3.1`。
- **不需要 readline**：源码树内不存在任何 readline 引用 —— 全树大小写不敏感
  检索 `readline` / `history.h` / `HAVE_READLINE` 只命中 `cmd_ed.c` 里名为
  `readLines` 的**内部静态函数**（行编辑器的按行读文件），与 GNU readline
  无关。sash 自己实现行输入，不链 readline。
- 其余为 libc / libm 等基础运行时；无构建期工具依赖。

## 许可证

上游 tarball **不含 LICENSE / COPYING 文件**，授权声明逐字写在每个源文件头部：

> Copyright (c) 2014 by David I. Bell
> Permission is granted to use, distribute, or modify this source,
> provided that this copyright notice remains intact.

这是一份「允许使用/分发/修改，条件是保留版权声明」的宽松授权，且**不含**
BSD 系列条款里的免责声明句，因此不强行套任何标准 SPDX 标识，配方里用
`LicenseRef-sash-custom` 表达（仓库内 `LicenseRef-*` 是既有写法）。

## 参考资料

- 上游作者主页 / 发布位：`https://members.tip.net.au/~dbell/`
  （tarball 托管于其 `programs/` 子目录；URL 路径中的 `~` 需百分号编码为 `%7E`）
- 版本：3.8（上游发布日期 2014-03-08，见包内 `CHANGES`）
- 语言：C；构建系统：GNU Make
