# netcat-openbsd

## 简介
netcat-openbsd 是 OpenBSD 系统的 nc (netcat) 重写版本，提供任意 TCP/UDP 连接和监听功能。

## OHOS 适配
- 构建系统: Makefile (GNU make)
- 应用 Debian 移植补丁实现 Linux/OHOS 平台兼容
- 提供 OHOS 兼容函数 (strtonum, readpassphrase, explicit_bzero, b64_ntop) 内联实现
- 不依赖外部 libbsd 库 (自包含配方)
- TLS 支持未包含 (libtls 来自 LibreSSL, 制品仓中不可用)

## 依赖
- 系统库: libresolv

## 功能验证
```bash
nc -h
```

## 参考
- 上游: https://salsa.debian.org/debian/netcat-openbsd
- 源码: snapshot.debian.org
