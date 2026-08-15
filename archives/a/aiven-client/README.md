# aiven-client — Aiven.io 官方命令行客户端

aiven-client（`avn`）是 Aiven 云服务的官方 Python 客户端库 / 命令行工具，
用于管理云服务实例、Kafka topic、VPC peering、认证令牌等。

## 特性

- 纯 Python 实现，无 C 扩展，跨平台（已适配 HarmonyOS PC arm64）
- `avn` 命令行入口（`aiven.client.__main__:main`）
- `AivenClient` API 客户端（认证、服务管理、审计日志等）
- 表格格式化（pretty）、拼写建议（speller）、命令行框架（argx）
- 运行时依赖 requests / requests-toolbelt / certifi

## 安装

```bash
pip3 install aiven-client
# 或经 Conan: conan create archives/a/aiven-client/4.16.0
```

## 上游地址

https://github.com/aiven/aiven-client

## 许可证

Apache License 2.0
