# tcping 2.1.0 for OpenHarmony

[![Status](https://img.shields.io/badge/status-built-success.svg)](https://opendesk.com)
[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/mkirchner/tcping)
[![Platform](https://img.shields.io/badge/platform-HarmonyOS-aarch64-orange.svg)](https://opendesk.com)

TCP Ping 实用工具 - 通过 TCP 连接测试网络端口可达性。

## 概述

tcping 是一个类似于传统 ping 的网络诊断工具，但它使用 TCP 协议而不是 ICMP 协议来测试网络连接。这使得 tcping 可以：

- 在没有 ICMP 权限的环境下使用
- 测试特定 TCP 端口的可达性
- 验证服务是否正在运行
- 穿过阻止 ICMP 的防火墙

## 与传统 ping 的区别

| 特性 | tcping | ping |
|------|--------|------|
| 协议 | TCP | ICMP |
| 需要 root 权限 | ❌ 不需要 | ❌ 不需要 |
| 需要 raw socket | ❌ 不需要 | ✅ 需要 |
| 测试端口可达性 | ✅ 支持 | ❌ 不支持 |
| 穿透防火墙 | ✅ 更好 | ⚠️ 可能被阻止 |
| HarmonyOS 兼容 | ✅ 完全兼容 | ⚠️ 可能受限 |

## 与 hping 的对比

| 特性 | tcping | hping |
|------|--------|-------|
| TCP 测试 | ✅ | ✅ |
| ICMP ping | ❌ | ✅ |
| UDP 测试 | ❌ | ✅ |
| 自定义 TCP 标志 | ❌ | ✅ |
| 需要 root 权限 | ❌ | ✅ |
| 需要 raw socket | ❌ | ✅ |
| 二进制大小 | 22KB | 较大 |
| 易用性 | ✅ 简单 | ⚠️ 复杂 |
| HarmonyOS 可用性 | ✅ 完全可用 | ❌ 受限 |

**推荐**: 在 HarmonyOS 环境下，推荐使用 tcping 进行简单的 TCP 端口连通性测试。

## 安装

### 从预编译包安装

```bash
# 解压
tar -xzf tcping-2.1.0-ohos-aarch64.tar.gz

# 安装
sudo cp bin/tcping /usr/local/bin/
sudo chmod 755 /usr/local/bin/tcping
```

### 本地安装

```bash
# 解压到用户目录
tar -xzf tcping-2.1.0-ohos-aarch64.tar.gz -C ~/usr/local/
```

## 使用方法

### 基本语法

```bash
tcping [-q] [-f <4|6>] [-t timeout_sec] [-u timeout_usec] <host> <port>
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `<host>` | 目标主机名或 IP 地址 |
| `<port>` | 目标端口号 |
| `-q` | 静默模式（只通过退出码返回结果） |
| `-f <4\|6>` | 强制使用 IPv4 或 IPv6 |
| `-t <sec>` | 设置超时时间（秒） |
| `-u <usec>` | 设置超时时间（微秒） |

### 使用示例

#### 基本端口测试

```bash
# 测试 SSH 端口
tcping localhost 22

# 测试 Web 服务器
tcping example.com 80
tcping example.com 443

# 测试 DNS 服务器
tcping 8.8.8.8 53
```

#### 设置超时

```bash
# 设置 3 秒超时
tcping -t 3 example.com 80

# 设置微秒级超时
tcping -u 500000 example.com 80
```

#### 强制使用 IPv4/IPv6

```bash
# 强制使用 IPv4
tcping -f 4 example.com 80

# 强制使用 IPv6
tcping -f 6 example.com 80
```

#### 静默模式（脚本中使用）

```bash
# 用于脚本判断
if tcping -q example.com 80; then
    echo "Port is open"
else
    echo "Port is closed"
fi
```

#### 在循环中监控端口

```bash
# 持续监控端口状态
while tcping -q localhost 8080; do
    echo "Port 8080 is open"
    sleep 5
done
echo "Port 8080 is closed"
```

### 退出码

| 退出码 | 说明 |
|--------|------|
| 0 | 端口开放（连接成功） |
| 1 | 端口关闭（连接被拒绝） |
| 2 | 连接超时 |
| 255 | 错误（参数错误、DNS 解析失败等） |

## 功能特性

✅ **TCP 端口连通性测试** - 测试 TCP 端口是否可达  
✅ **IPv4/IPv6 支持** - 支持 IPv4 和 IPv6 协议  
✅ **DNS 解析** - 支持主机名解析  
✅ **超时控制** - 支持秒级和微秒级超时设置  
✅ **静默模式** - 适合脚本使用  
✅ **无权限需求** - 普通用户即可使用  
✅ **轻量级** - 仅 22KB 二进制文件  

## 常见用例

### 1. 检查 Web 服务器状态

```bash
# 检查 HTTP 服务
tcping www.example.com 80

# 检查 HTTPS 服务
tcping www.example.com 443
```

### 2. 检查 SSH 服务

```bash
tcping server.example.com 22
```

### 3. 检查数据库端口

```bash
# MySQL
tcping db.example.com 3306

# PostgreSQL
tcping db.example.com 5432

# Redis
tcping db.example.com 6379
```

### 4. 检查邮件服务

```bash
# SMTP
tcping mail.example.com 25

# IMAP
tcping mail.example.com 143

# POP3
tcping mail.example.com 110
```

### 5. 检查防火墙规则

```bash
# 测试防火墙是否允许特定端口
tcping firewall.example.com 8080
```

### 6. 服务健康检查

```bash
#!/bin/bash
# health-check.sh

HOST="example.com"
PORT=80

if tcping -q -t 2 $HOST $PORT; then
    echo "✅ Service is healthy"
    exit 0
else
    echo "❌ Service is down"
    exit 1
fi
```

## 限制

- ❌ 不支持 ICMP ping（请使用 `ping` 命令）
- ❌ 不支持 UDP 测试（请使用 `nc` 或 `hping`）
- ❌ 不支持自定义 TCP 标志（请使用 `hping`）
- ❌ 不支持持续探测模式（请使用脚本循环）
- ❌ 不显示延迟统计信息

## 故障排除

### 问题 1: "Name does not resolve"

**原因**: DNS 解析失败  
**解决**: 
- 检查主机名是否正确
- 使用 IP 地址代替主机名
- 检查 DNS 服务器配置

### 问题 2: "Unrecognized service"

**原因**: 端口号无效  
**解决**: 
- 使用有效的端口号（1-65535）
- 确保端口号是数字格式

### 问题 3: 连接超时

**原因**: 
- 目标主机不可达
- 端口被防火墙阻止
- 网络延迟过高

**解决**: 
- 增加超时时间: `tcping -t 10 host port`
- 检查防火墙规则
- 使用 `ping` 测试基本连通性

### 问题 4: IPv6 解析失败

**原因**: 主机没有 IPv6 地址  
**解决**: 
- 使用 `-f 4` 强制 IPv4: `tcping -f 4 host port`

## 技术细节

### 二进制信息

```
文件类型: ELF shared object
架构: 64-bit LSB arm64
链接: 动态链接 (/lib/ld-musl-aarch64.so.1)
大小: 22KB
```

### 依赖

- ✅ musl libc (系统自带)
- ❌ 无其他外部依赖

### 构建信息

- 编译器: clang 15.0.4
- 构建系统: Makefile
- 构建日期: 2026-05-14

## 相关文档

- [构建报告](reports/build-report.md) - 详细的构建过程
- [测试报告](reports/test-report.md) - 功能测试结果
- [质量报告](reports/quality-report.md) - 质量门禁检查
- [编译笔记](notes.md) - 编译过程记录

## 许可证

Copyright (c) 2002-2023 Marc Kirchner

## 原始项目

- GitHub: https://github.com/mkirchner/tcping
- 作者: Marc Kirchner
- 版本: 2.1.0

---

**OpenHarmony 编译版本** | 构建于 2026-05-14