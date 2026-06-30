# websocat

WebSocket 客户端命令行工具，用于 WebSocket 连接、调试和测试。

## 基本信息

- **语言**: Rust
- **类型**: WebSocket 客户端/命令行工具
- **官方网站**: https://github.com/vi/websocat
- **源码**: https://github.com/vi/websocat

## 功能特性

- WebSocket 客户端和服务器模式
- 支持多种协议转换（WebSocket <-> TCP, Stdin, 等）
- 静态编译，无依赖

## 版本信息

| 版本 | 状态 | 编译方式 |
|------|------|---------|
| 1.14.0-r1 | published | 官方预编译包（aarch64-musl） |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- websocat 1.14.0-r1
```

## 使用示例

```bash
# 连接 WebSocket 服务器
websocat ws://echo.websocket.org

# 版本检查
websocat --version

# 帮助信息
websocat --help
```
