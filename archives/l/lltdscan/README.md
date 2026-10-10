# lltdscan 0-20180223 — OpenHarmony 编译记录

## 基本信息
- 软件: lltdscan
- 版本: 0-20180223（赛事平台任务 #8518 指定的版本号；上游无 tag/release）
- 构建系统: makefile（无 configure，单 Makefile）
- 目标: ohos-aarch64
- 依赖: libpcap/1.10.6、libnet/1.2

## 编译指导
- Raw Makefile: `make CC=<工具链 clang> "CFLAGS2=-g -O2 -I<libpcap include> -I<libnet include>" "LDFLAGS2=-g -L<libpcap lib> -L<libnet lib>" -j1`
- 上游 CFLAGS2/LDFLAGS2 指向 `/usr/local`、`/usr/include/pcap`、`/opt/csw`
  （arping/Solaris 遗留），用 make 命令行同名变量整体覆盖，不必改源码
- Makefile 链接行本就使用 `$(CC)`，无需编译器变量补丁
- make -j1（HMDFS jobserver FIFO EPERM，E074）

## 补丁清单
- 无。源码零改动。

## 已知限制
- 上游无测试套件（Makefile 仅 all/lltdscan/clean/doc/install/dist 目标，
  全树 6 个文件无任何测试源），功能验证由 test_package 真实执行
  lltdscan 二进制完成，覆盖 `-h` / 非法选项 / 参数校验等 5 例 19 断言
- 真实抓包需混杂模式 + root + 对端运行 LLTD responder，CI 不可复现，
  test 里绝不裸跑 `lltdscan`（会阻塞到超时）
- 保留 7 个上游 warning（`-Wpointer-sign` / `-Wformat` /
  `-Wdeprecated-declarations`），属上游 2009-2013 年代码风格，不在适配范围

## 功能验证
- test_package/test.sh: `-h` 用法横幅完整性与 exit 0、未知选项被拒、
  `-t` 缺参数被拒、畸形 MAC 被拒、两个尾随 MAC 打印用法并 exit 1