# tcping

TCP Ping 工具 - 检测 TCP 端口是否可达。

## 软件简介

tcping 是一个命令行工具，用于测试 TCP 端口连接性。与传统使用 ICMP 的 ping 不同，tcping 通过建立 TCP 连接来判断端口是开放、关闭还是超时。

## 使用方法

```bash
tcping [-q] [-f <4|6>] [-t timeout_sec] [-u timeout_usec] <host> <port>
```

### 参数说明

- `-q`: 安静模式（抑制输出）
- `-f <4|6>`: 强制使用 IPv4 或 IPv6
- `-t timeout_sec`: 超时时间（秒）
- `-u timeout_usec`: 超时时间（微秒）

### 使用示例

```bash
# 测试本地端口 80 是否开放
tcping localhost 80

# 测试 SSH 端口并设置超时
tcping -t 5 example.com 22

# 安静模式测试
tcping -q example.com 443
```

## 依赖关系

- 无外部依赖（仅使用标准 C 库）

## OpenHarmony 适配

- 使用 clang 编译器
- 修改 Makefile 支持 DESTDIR 安装
- 添加 install 目标用于打包

## 构建系统

- 类型: Makefile（简单，无 autotools）
- 编译器: clang

## 许可证

Copyright (c) 2002-2023 Marc Kirchner