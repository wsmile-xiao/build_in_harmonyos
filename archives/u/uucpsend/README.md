# uucpsend

`uucpsend` 是 INN（InterNetNews）的 UUCP 批处理前端，作者 Martin Schulze，
用来替代 INN 自带的 `send-uucp` 脚本。它按站点控制文件调度 `ctlinnd`、
`batcher` 与 `uux`，完成 Usenet 文章经 UUCP 链路的批量投递。

## 简介

程序本身不做批处理压缩/打包，而是做一个**调度器**：为每个配置好的站点
加锁、检查 UUCP spool 剩余空间、要求 INN 刷新该站点的待发队列、把上一轮
的残留工作文件合并去重，最后以 `uux -gd <site>!rnews` 为投递命令驱动
`batcher` 生成批次。站点级参数（队列上限、单批上限、头部、压缩器、
额外 uux 参数）全部写在 `uucpsend.ctl` 里。

上游发布包极小：`uucpsend.c`（620 行）+ `log.c`（75 行）+ 手写 POSIX
Makefile + 两份 man 页 + 示例控制文件。

## OHOS 适配

- **构建系统**：手写 POSIX Makefile，无 configure / CMake / meson。
- **零链接期依赖**：只使用 libc。对 INN 与 Taylor UUCP 的耦合全部经由
  `system(3)`/`popen(3)` 子进程，程序内不含任何第三方链接符号。
- **补丁 0001**（Makefile，可移植性）：补 `all:` 默认目标（上游连 `all`
  都没有）；`CC/CFLAGS/CPPFLAGS/LDFLAGS` 改 `?=`，使 Conan 经 `conanbuild`
  环境脚本注入的工具链真正生效；`STRIP` 仅在未设 `DEBUG` 时取 `-s`；
  install 规则加 `DESTDIR` 分期 + `BINDIR/CONFDIR/MANDIR` 可覆盖，并去掉
  无条件的 `-o root -g root`（非 root 构建必然失败）与 `install -d`；
  `SHELL` 固定 `/bin/sh`（OHOS 无 `/bin/bash`）。
- **补丁 0002**（uucpsend.c，可移植性）：`index()` → `strchr()`（5 处）；
  删除 `<malloc.h>`。musl 仅在 `_BSD_SOURCE` 下声明 `index()`，且不提供
  `<malloc.h>`。
- **补丁 0003**（uucpsend.c，可移植性/上游缺陷）：`free_sites()` 的形参写成
  了程序中并不存在的 `struct s_sites *`，函数体又对强制转换赋值
  `(struct s_sites *)act = ...`；clang 15 把「对 cast 赋值」判为硬错误而非
  仅警告，**未打补丁的上游源码在 OHOS 工具链下无法编译**。改为
  `struct s_site *` 形参并直接赋值，同时消除 3 处
  `-Wincompatible-pointer-types`。真机首轮构建实测发现。
- **打包方式**：`make DESTDIR=<stage> install` 到构建目录内的暂存树，再由
  配方显式复制到 `bin/`、`share/man/`、`share/uucpsend/`、`share/doc/`，
  不向宿主机 `/etc` 写任何东西。
- **未改动**：`paths.h` 中的 `/var/spool/news`、`/usr/lib/news/bin`、
  `/usr/bin/uux` 等绝对路径保持上游原样——它们是 INN/UUCP 的标准位置，
  改成可配置属于功能变更，超出适配范围，同样会导致无法在本机脱离
  INN 部署真实投递。

## 依赖

**链接期**：无第三方 Conan 依赖，仅目标平台 libc。

**运行期（非 Conan 依赖，需部署侧提供）**：`ctlinnd` 与 `batcher`
（由 `inn2` 提供，制品仓中 `inn2/2.7.4` 已发布）、`uux`（由 `uucp` 提供，
**`uucp/1.07` 尚未发布到制品仓**），以及 `df`/`du`/`sort`/`mv`/`cat`/`rm`
等系统工具。详见 `1.1/notes.md` 与 `1.1/manifest.yaml` 的
`runtime_prerequisites`。

## References

- Homepage: https://www.infodrom.org/projects/uucpsend/
- uucpsend(8): https://www.infodrom.org/projects/uucpsend/uucpsend.8.php
- uucpsend.ctl(5): https://www.infodrom.org/projects/uucpsend/uucpsend.ctl.5.php
- Source: https://www.infodrom.org/projects/uucpsend/download/uucpsend-1.1.tar.gz
  (sha256 `3447ff358e21c9927f4a35409218bf6f77c6caaceeed298bc15a8cb6dec065bc`；
  Debian 的 pristine orig 包与之逐字节相同，作为等价镜像列出)
- Debian packaging (patches we did not need): https://salsa.debian.org/debian/uucpsend
