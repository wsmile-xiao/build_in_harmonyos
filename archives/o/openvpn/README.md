# openvpn

OpenVPN secure VPN daemon，用于创建安全的 VPN 连接。

## 基本信息

- **语言**: C
- **类型**: VPN 守护进程
- **官方网站**: https://openvpn.net/
- **源码**: https://github.com/OpenVPN/openvpn

## 功能特性

- SSL/TLS 加密隧道
- 多种认证方式
- TCP/UDP 协议支持
- 路由和桥接模式

## 版本信息

| 版本 | 状态 | 构建系统 | 补丁数 |
|------|------|----------|--------|
| 2.6.16 | published | autotools | 1 |

## 依赖

- OpenSSL
- LZO
- lz4

## 使用说明

```bash
openvpn --version
openvpn --config client.ovpn
```

## 编译说明

需要以下补丁：
- networking_sitnl.c 网络接口兼容性补丁