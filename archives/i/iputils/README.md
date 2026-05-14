# iputils — OpenHarmony 预编译包

Linux 网络诊断工具集合，包含 ping、tracepath 等核心网络工具。

## 可用版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 20240905 | SUCCESS | 2026-05-06 |

## 包含工具

### ping — ICMP Echo 工具
- **功能**: 检测网络连通性
- **IPv4**: ✅ 支持
- **IPv6**: ✅ 支持（使用 `-6` 选项或自动检测）
- **特性**: IPv4/IPv6 统一接口，替代传统 ping + ping6

### tracepath — 路径追踪工具
- **功能**: 路径 MTU 发现，追踪网络路径
- **IPv4**: ✅ 支持
- **IPv6**: ✅ 支持（使用 `-6` 选项或自动检测）
- **特性**: IPv4/IPv6 统一接口，替代传统 traceroute + traceroute6

### arping — ARP 请求工具
- **功能**: 发送 ARP 请求，检测局域网设备
- **IPv4**: ✅ 支持
- **IPv6**: ❌ 不支持（ARP 协议限制）

### clockdiff — 时钟差测量
- **功能**: ICMP Timestamp 测量时钟差异
- **IPv4**: ✅ 支持
- **IPv6**: ❌ 不支持（ICMP Timestamp 协议限制）

## 安装方法

```bash
cd /path/to/archives/i/iputils/
./install.sh
```

或指定版本：
```bash
cd 20240905/packaging/
./install-iputils-20240905.sh
```

## 使用示例

### ping（IPv4/IPv6）
```bash
# IPv4 ping
ping 192.168.1.1

# IPv6 ping
ping -6 ::1
ping ::1  # 自动检测 IPv6
```

### tracepath（IPv4/IPv6）
```bash
# IPv4 tracepath
tracepath 192.168.1.1

# IPv6 tracepath
tracepath -6 ::1
tracepath ::1  # 自动检测 IPv6
```

### arping
```bash
arping -I eth0 192.168.1.1
```

## 关键特性

1. **IPv4/IPv6 统一设计**: 使用单一工具替代传统的 IPv4/IPv6 分离工具
2. **musl libc 支持**: 兼容 musl libc 环境
3. **无 setcap/setuid**: 避免权限问题，使用 `-DNO_SETCAP_OR_SUID=true`

## 与 inetutils 对比

| 功能 | inetutils | iputils |
|------|-----------|---------|
| ping IPv4 | ✅ ping | ✅ ping |
| ping IPv6 | ✅ ping6（独立工具） | ✅ ping -6（统一工具） |
| traceroute | ✅ traceroute | ❌ |
| traceroute6 | ❌ | ❌ |
| tracepath | ❌ | ✅ tracepath |
| tracepath IPv6 | ❌ | ✅ tracepath -6 |

## 源码

- 官方源码: https://github.com/iputils/iputils
- 构建系统: meson