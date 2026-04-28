# dnsmasq 2.92 适配笔记

## 编译环境
- 构建系统: makefile (无 configure)
- 编译日期: 2026-04-28
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
```bash
make PREFIX=$HOME/usr/local
make install PREFIX=$HOME/usr/local DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重复定义 | linux/socket.h 和 sys/socket.h 都定义 | 补丁 0001/0002: 定义 _UAPI_LINUX_SOCKET_H 并手动提供 typedef |

## 源码修改
- 0001-src-ipset.c.patch: 修复 sockaddr_storage 冲突
- 0002-src-netlink.c.patch: 修复 sockaddr_storage 冲突

## 验证结果
- dnsmasq --version 显示 Dnsmasq version 2.92rc3

## 交付物
- sbin/dnsmasq

## 注意事项
- 7 个 sign-compare 警告（来自 CMSG_NXTHDR 宏），不影响功能
- 包含 <linux/netlink.h> 的代码在 OpenHarmony 上需要 sockaddr_storage 修复
