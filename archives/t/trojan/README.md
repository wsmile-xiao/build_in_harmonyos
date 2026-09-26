# trojan

trojan - an unidentifiable mechanism that helps you bypass GFW。

## 软件简介

trojan 是一个 HTTPS 代理工具（C++17，CMake 构建），仿照 HTTPS 流量伪装代理协议：
server 与 client 共用同一协议栈，走标准 TLS 传输，依赖 boost（system +
program_options）与 openssl。本目录为其 HarmonyOS PC (aarch64) 适配归档。

## 目录结构

- `1.16.0/` — Conan 配方（conanfile.py + conandata.yml + patches/ + test_package/）
- `commands.json` — 命令行工具入口声明（R38）

## 使用方法

```bash
trojan -v                     # 版本
trojan -t <config.json>       # 配置校验
trojan <config.json>          # 以 server/client/forward 配置启动
```

配置示例见包内 `share/doc/trojan/examples/`（server/client/forward/nat）。

## 适配版本

- 1.16.0（上游 v1.16.0 tag archive，官方源 GitHub trojan-gfw/trojan）
