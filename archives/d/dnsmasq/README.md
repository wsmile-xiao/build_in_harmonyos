# dnsmasq

## 简介
dnsmasq 是一个轻量级 DNS 转发器、DHCP 服务器和 TFTP 服务器。

## OHOS 适配
- 使用 Makefile 构建，无 configure 脚本
- OpenHarmony 系统头文件中 `linux/socket.h` 和 `sys/socket.h` 都定义了 `struct sockaddr_storage`
- 包含 `<linux/netlink.h>` 的代码需要定义 `_UAPI_LINUX_SOCKET_H` 并手动提供 `__kernel_sa_family_t` typedef

## 依赖
无外部依赖。

## 功能验证
```bash
dnsmasq --version
```

## 参考
- 官网: https://thekelleys.org.uk/dnsmasq/doc.html
