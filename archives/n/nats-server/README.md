# nats-server

NATS.io 高性能服务器 - 云原生消息传递系统

## 简介

nats-server 是 NATS 消息传递系统的服务器组件。NATS 是一个开源的、轻量级的、高性能的消息传递系统，支持发布-订阅、请求-回复和队列模式。

## 版本信息

### v2.12.6 (当前版本)
- **编译日期**: 2026-05-29
- **编译器**: go1.25.10
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64
- **编译方式**: Go 静态编译 (CGO_ENABLED=0)
- **质量门禁**: G1-G4 通过

## 功能特性

- 高性能消息传递
- 发布-订阅模式
- 请求-回复模式
- 队列模式
- 持久化支持 (JetStream)
- 集群支持
- 安全认证

## 使用方法

### 启动服务器
```bash
nats-server
```

### 查看版本
```bash
nats-server --version
```

### 查看帮助
```bash
nats-server --help
```

### 配置文件
```bash
nats-server -c /path/to/config.conf
```

## 安装

使用 cmd-pkgs 公共安装脚本安装预编译包：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- nats-server v2.12.6
```

## 已知问题

1. **Go 项目特性**: 静态编译，无外部依赖
2. **HMDFS 限制**: 在某些目录下可能无法执行（权限问题）
3. **测试限制**: 未进行完整的功能测试（服务器启动等）

## 参考

- 官方网站: https://nats.io
- GitHub: https://github.com/nats-io/nats-server
- 文档: https://docs.nats.io

---
*最后更新: 2026-05-29*