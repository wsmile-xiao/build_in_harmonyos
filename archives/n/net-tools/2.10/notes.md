# net-tools 2.10 - 适配笔记

## 概述
net-tools（legacy NET-3）Linux 网络工具集：ifconfig/route/netstat/arp/rarp/hostname/nameif/iptunnel/ipmaddr/mii-tool/plipconfig/slattach。本次适配官方 sourceforge 发布版 net-tools-2.10.tar.xz。

## 编译环境
- 构建系统: makefile（configure.sh config.in + 顶层 Makefile，非 autotools）
- 交叉编译: clang 15 (BiSheng / OHOS aarch64 target) + OHOS musl sysroot
- 编译日期: 2026-09-03
- 状态: built（conan-verify G0-G4/L1 通过；L2 SKIP、L4 WARN，因 OHOS 需 sign-elf 未做真机签名执行验证）

## 编译步骤
1. 非交互 configure：`yes "" | bash ./configure.sh config.in`（接受裁剪后默认值）
2. 交叉编译：`CPPFLAGS=-D__MUSL__ make CC=<ohos-clang> AR=llvm-ar RANLIB=llvm-ranlib -j1`
3. 产物 12 个工具：ifconfig/netstat/route/hostname(→/bin)，nameif/arp/rarp/iptunnel/ipmaddr/mii-tool/plipconfig/slattach(→/sbin)
4. ELF 验证：ELF64 AArch64 PIE，interpreter /lib/ld-musl-aarch64.so.1，仅依赖 libc.so

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ipx.h not found` 等 | config.in 默认开启 IPX/ATALK/AX25 等协议族及 ARC 硬件，OHOS musl sysroot 缺对应头文件 | 裁剪 config.in 默认值（补丁 0001）：禁 IPX/ATALK/AX25/NETROM/ROSE/X25/ASH 协议族、ARC/AX25/ROSE/NETROM/X25/ASH/IrDA/EUI64/IB 硬件 |
| 2 | `undefined symbol: rindex`（hostname 链接失败） | OHOS musl `<strings.h>` 只声明 `index()`/`bzero()`，不声明 `rindex()`（glibc 兼容遗留） | 替换为标准 C `strchr()`/`strrchr()`（补丁 0002/0003），跨 libc 安全 |
| 3 | `sockaddr_storage` redefinition（潜在） | OHOS musl `<sys/socket.h>` 仅 `__MUSL__` 下定义 sockaddr_storage | 编译强制 `-D__MUSL__`（3.14-alpha 同款经验） |

## 源码修改
- `patches/0001-config.in.patch`：config.in 默认值裁剪
- `patches/0002-hostname.c.patch`：index/rindex → strchr/strrchr
- `patches/0003-netstat.c.patch`：rindex → strrchr

## 依赖版本
- 无外部依赖（纯 libc）

## 验证结果
- conan-verify G0-G4/L1 通过；L2/L4 SKIP（OHOS 需 sign-elf，未做真机签名执行验证）
- 产物 ELF64 AArch64 PIE，strings 含 "net-tools 2.10"

## 注意事项
- ELF 需 sign-elf 签名后才能在鸿蒙设备执行（平台常规，CI sign.sh 处理）
- 禁用的协议族/硬件类型对应功能在鸿蒙生态无对应内核子系统，裁剪合理
- 上游无独立测试框架（make check 无目标），以 test_package test.sh 验证打包二进制
---

**编译结束**: 2026-09-03 17:26
**最终状态**: built
