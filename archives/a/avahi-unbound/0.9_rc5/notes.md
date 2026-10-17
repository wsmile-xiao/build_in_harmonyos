# 适配笔记 — avahi-unbound 0.9_rc5

## 概述

avahi-unbound 是 Alpine Linux 的 avahi 子包，为 unbound DNS 解析器提供 mDNS 集成配置文件。
本包为**纯配置包**，不包含编译步骤，不产出二进制或库文件。

## 源码

- 上游源码：https://github.com/avahi/avahi/archive/refs/tags/v0.9-rc5.tar.gz
- sha256: `5b0a9d88110b0fc8aaafc5cc0a26e83e7d2a4aca3a36bc27c9b626db7ead27b0`
- 与 avahi-compat-libdns_sd / avahi-glib 使用同一源码 tarball（版本一致性）
- 配置文件内容源自 Alpine Linux aports 仓库（main/avahi/unbound.conf）

## 构建过程

1. `source()`：下载 avahi tarball（用于 sha256 校验和版本一致性）
2. `build()`：生成 `avahi.conf` 配置文件（内容与 Alpine aports 一致）
3. `package()`：安装至 `etc/unbound/unbound.conf.d/avahi.conf`

## 配置文件内容

```
forward-zone:
	name: "local"
	forward-addr: 127.0.0.1@5354
server:
	do-not-query-localhost: no
	domain-insecure: "local"
```

- `forward-zone`：将 `.local` 区域查询转发至 avahi-daemon DNS 代理
- `forward-addr: 127.0.0.1@5354`：avahi-daemon DNS 代理监听端口
- `do-not-query-localhost: no`：允许转发到 localhost
- `domain-insecure: "local"`：mDNS 不支持 DNSSEC

## 测试

- 上游无测试用例（配置文件不在 avahi 源码中，由 Alpine aports 维护）
- test_package 提供 7 个自定义断言验证配置文件内容（文件存在、forward-zone、name、forward-addr、server、do-not-query-localhost、domain-insecure）

## 依赖

- unbound 1.22.0（运行时依赖，已发布到制品仓）
---

**编译结束**: 2026-08-27 03:51
**最终状态**: published
