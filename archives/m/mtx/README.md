# mtx — SCSI 磁带库/机械手控制工具集

MTX（Media Changer Tools）用于控制 SCSI 机械手与磁带库（autoloader / tape library），
也直接操作磁带机。它通过 SCSI 透传接口发送 READ_ELEMENT_STATUS、MOVE_MEDIUM、
INQUIRY、REQUEST_SENSE 等命令，是备份软件（如 Bacula、Amanda）在 Linux 上驱动
磁带库的常用底层工具。

## 功能概述

- **机械手控制**: `mtx` 提供 `status`/`inventory`/`load`/`unload`/`transfer`/`exchange`/
  `first`/`last`/`next`/`previous`/`position`/`eject` 等完整媒体交换命令
- **磁带机操作**: `scsitape` 支持 `setblk`/`fsf`/`bsf`/`eod`/`rewind`/`mark`/`seek`/
  `read`/`write` 等 SCSI 磁带命令
- **托盘控制**: `scsieject` 提供 `load`/`unload`/`start`/`stop`/`lock`/`unlock`
- **设备信息**: `tapeinfo` 打印磁带机状态（密度、块大小、压缩、缓冲等），
  `loaderinfo` 打印机械手元素状态
- **多平台 SCSI 后端**: Linux/OHOS 走 SCSI generic（`SG_IO`），另有 FreeBSD/Solaris/
  AIX/HP-UX/SGI/Windows 后端，编译期按头文件探测自动选择

## OHOS 适配要点

### 平台三元组（config.guess / config.sub）

tarball 内置的是 2008 年前后的 autoconf 辅助脚本，三个坑：

- `config.sub` 的 `maybe_os` 白名单只到 `linux-uclibc*`，遇到
  `--host=aarch64-linux-ohos` 会**硬失败**：
  `Invalid configuration 'aarch64-linux-ohos': machine 'aarch64-linux' not recognized`，
  configure 随即报 `config.sub $host_alias failed` 并以 exit 1 终止。
- 更隐蔽的是，同一份 `config.sub` 的 basic_machine 白名单里**没有 `aarch64`**
  （当年只有 `arm`/`armv[2345]` 等）。只补 `linux-ohos` 仍会报
  `machine 'aarch64' not recognized`，必须同时补 `aarch64 | aarch64_be`。
- `config.guess` 没有 HarmonyOS 分支，而真机 `uname -s` 返回 `HarmonyOS`；
  configure 的 `AC_CANONICAL_SYSTEM` 无条件调用它推导 build 三元组，
  识别失败时会落到末尾 fallback —— 去编译 `dummy.c`。

### HMDFS 临时目录（umask）

`config.guess` 与 autoconf 2.13 生成的 `configure`（config.status 段）都用
`umask 077 && mktemp -d` 建临时目录。在 HarmonyOS 的 HMDFS 上，这样建出的目录
**对后续写入不可用**，真机表现为：

```text
config.guess: line 1307: .../tmp/cgXXXXXX/dummy.c: Permission denied
config.guess: unable to guess system type
```

两处 `umask 077` 都要改成 `umask 022`。另外真机 `/tmp` 只读，构建脚本必须显式
`TMPDIR=$HOME/...`。

### 无需修改平台分支与 SCSI 后端

- `configure.in` 的平台分支写作 `case "$host_os" in *linux*)`，`linux-ohos` **能匹配**，
  因此 `TARGET=linux`、`AC_DEFINE(LINUX)`、`Makefile.in` 的
  `ifeq ($(TARGET),linux)` 分支（`-Wall -DLONG_PRINT_REQUEST_SENSE=1`）全部按上游
  Linux 路径生效，不需要加 `ohos` 分支或 `__OHOS__` 宏。
- `scsi_linux.c` 通过 `#ifdef SG_IO` 使用 `sg_io_hdr_t` + `ioctl(fd, SG_IO, ...)`，
  需要 `<scsi/sg.h>`；`SCSI_GetIDLun()` 需要 `<scsi/scsi.h>` 的 `SCSI_IOCTL_GET_IDLUN`；
  `scsitape` 的 tape 操作需要 `<sys/mtio.h>` 的 `MTIOCTOP`。HarmonyOS PC 的 clang
  sysroot 实测自带这四个头文件，所以 **不需要 stub、不需要裁剪功能**。
- 真机上 `mtx -f <普通文件> status` 返回内核真实错误
  `is not an sg device, or old sg driver`，证明 `SG_IO` 后端确实编进了二进制。

### 与 Linux 的差异

| 差异点 | Linux | OHOS | 说明 |
|--------|-------|------|------|
| 平台三元组 | aarch64-unknown-linux-gnu | aarch64-unknown-linux-ohos | config.guess/sub 需要补丁，且 config.sub 需补 aarch64 机器名 |
| `uname -s` | Linux | HarmonyOS | config.guess 必须有 HarmonyOS 分支 |
| 临时目录 | `/tmp` 可写、umask 077 可用 | `/tmp` 只读、HMDFS 下 umask 077 目录不可写 | 必须设 `TMPDIR`，并把 umask 改 022 |
| 二进制签名 | 不需要 | 未签名 ELF `Permission denied` | 必须用带 `-Wl,--code-sign` 的 wrapper clang |
| 构建布局 | 常见源内构建 | Conan `basic_layout` 源外构建 | install 目标需从 `$(srcdir)` 取 man 页，否则 `make install` 失败 |
| SCSI 透传 | `/dev/sg*` + `SG_IO` | 同名接口；设备节点由内核/驱动决定 | 代码路径一致，差异在设备可用性 |
| 机械手设备 | `/dev/changer` 常为 udev 建的符号链接 | 无 udev 规则 | 需要用 `-f` 指定真实设备节点 |
| 自带 `patch` | GNU patch | 精简实现（无 `--forward`/`-N`） | 手工验补丁用 `/data/service/hnp/bin/git apply` |

## 依赖关系

### 编译依赖

无外部编译依赖。仅需 C 编译器 + GNU make（上游 `Makefile.in` 用 `ifeq`、`$(BINS:...)`
等 GNU 扩展，BSD make 不可用）。

### 运行依赖

无。5 个二进制只链接 libc。

## 运行边界

MTX 的所有实际功能都需要**真实 SCSI 机械手/磁带机**。没有硬件时：

- `mtx --version` 打印 banner（上游实现随后调用 `Usage()`，退出码为 1）；
- `mtx noattach` 是纯状态命令，不需要设备，退出码 0；
- 其余命令会打开 `$CHANGER` → `$TAPE` → `/dev/changer`，失败时打印 SCSI 错误并退出 1。

因此 `test_package` 的断言限定在 CLI 层与“确实进入了 SCSI 后端”这一事实，
不宣称已验证数据通路。

## 已归档版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.3.12 | built | 2026-09-29 | 3 个平台适配补丁（config.guess / config.sub / Makefile.in DESTDIR） |

## 参考资料

- **官网 / 源码**: https://sourceforge.net/projects/mtx/
- **许可证**: GPL-2.0-or-later
- **上游版本**: 1.3.12（2008-08，上游最后一个稳定版）
