# rbootd 3.4 — OpenHarmony 编译记录

## 基本信息
- 软件: rbootd（Remote Boot Daemon，HP 工作站远程引导守护进程）
- 版本: 3.4
- 构建系统: makefile（无 configure，单一多分支 Makefile）
- 目标: ohos-aarch64
- 依赖: libpcap/1.10.6
- 上游: https://git.kernel.org/pub/scm/linux/kernel/git/deller/rbootd.git
- 源码: https://deb.debian.org/debian/pool/main/r/rbootd/rbootd_3.4.tar.xz

## 编译指导
- Raw Makefile:
  `make CC=<工具链 cc> CFLAGS="-O2 -Wall -Wno-unused-variable -I<libpcap include>" LDFLAGS="-L<libpcap lib>" -j1`
- Makefile 自带 `$(CC)` 与 `LFLAGS += -lpcap`；libpcap 以静态库链接
- make -j1（HMDFS jobserver FIFO EPERM，E074）

## 补丁清单
- 0001-Makefile.patch — 平台分支同时匹配 Linux/HarmonyOS（`uname -s` 在 HarmonyOS 返回 "HarmonyOS"，否则落入 BSD 分支 `.include <bsd.prog.mk>` 报 missing separator）
- 0002-defs.h.patch — 显式 `#include <sys/types.h>` 提供 BSD 类型（OHOS/musl 的 `<sys/param.h>` 不传递提供）；补 `__P()` 原型宏回退（glibc `<sys/cdefs.h>` 提供，musl 无）
- 0003-rmpproto.c.patch — `rindex()` 改 `strrchr()`（musl 不导出 rindex，链接 undefined symbol）

## 已知限制
- 上游 rbootd 3.4 无测试套件（Makefile 仅 rbootd/clean/all/install 目标），功能验证由 test_package 真实执行 rbootd 二进制（getopt 启动路径）完成
- `rbootd` 运行时需 root 与真实抓包网卡，test_package 仅覆盖安全启动路径，不做真实抓包
- 上游 `make install` 依赖 `install -o root -g root`，OHOS 无 `install` 命令，package() 直接拷贝产物

## 功能验证
- test_package/test.sh: 3 断言（其中 OHOS 特有 2 项）
  1. `rbootd -d -Z` 执行并 getopt 拒绝无效选项
  2. OHOS 特有: 产物为 aarch64 + `/lib/ld-musl-aarch64.so.1` 的 OHOS ELF（e_machine=0xB7）
  3. OHOS 特有: libpcap 静态链接（无 `libpcap.so` 动态依赖）
