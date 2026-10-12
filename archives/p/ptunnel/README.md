# ptunnel — OpenHarmony 编译档案

## 软件简介
ptunnel（Ping Tunnel，Daniel Stoedle）是一个利用 **ICMP echo request/reply（ping）
报文**把 TCP 连接可靠隧穿到远端主机的命令行工具，客户端 + 代理双模式、单二进制
`ptunnel`。常用于受限制网络（只放行 ICMP、不放行 TCP/UDP）下访问远端服务。
许可证 BSD-3-Clause。本次适配上游发布版 **0.72**（作者站点
https://www.cs.uit.no/~daniels/PingTunnel/ 官方归档）。

## OHOS 适配要点
- 纯 Makefile 单二进制（无 configure/autotools），`CC = gcc` 硬编码：
  `make CC=<OHOS clang>`（make 命令行变量优先于 Makefile 内赋值）即可构建。
- 依赖 **libpcap/1.10.6**（制品仓已发布）：pcap 头路径注入 CFLAGS、库路径注入
  LDOPTS（该 Makefile 编译规则用 CFLAGS、链接规则用 LDOPTS，从不引用
  CPPFLAGS/LDFLAGS）。ptunnel.h 用 `#include <pcap.h>`，libpcap 头安装于
  `include/pcap/pcap.h`，故 `-Iinclude` 与 `-Iinclude/pcap` 同时给出。
- pthread 由 OHOS libc 提供（`-lpthread` 兼容）；selinux 分支因无
  `/usr/include/selinux/selinux.h` 自动不启用。
- 上游 `make install` 用 coreutils `install`，`package()` 手动复制
  `bin/ptunnel`、`share/man/man8/ptunnel.8`、`licenses/LICENSE`。
- 上游**无任何测试目标/测试目录**（Makefile 仅 all/dist/ptunnel/clean/depend/
  install）；test_package 以 `-h` 冒烟验证（打印 `Usage:` + `ptunnel v` 横幅且
  非零退出）。完整隧穿需 root + 抓包设备 + 实时 ICMP，构建沙箱不可运行。

## 依赖关系
- 编译/运行依赖: `libpcap/1.10.6`（pthread 由系统 libc 提供）
- 被依赖: 无（独立 CLI 工具）

## 参考资料
- [ptunnel 官方主页](https://www.cs.uit.no/~daniels/PingTunnel/)
- [0.72 官方源码归档](https://www.cs.uit.no/~daniels/PingTunnel/PingTunnel-0.72.tar.gz)
