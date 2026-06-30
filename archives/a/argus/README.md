# argus

**Argus** — Audit Record Generation and Utilization System

Argus 是一个网络流量审计系统，用于实时 IP 网络流量的审计和数据记录。
它基于 libpcap 进行网络数据包捕获，生成网络流量记录（Argus Flow Records），
支持多种网络协议分析。

## 已编译版本

| 版本 | 状态 | 平台 | 构建系统 |
|------|------|------|----------|
| 5.0.2 | published | HarmonyOS aarch64 | autotools |

## 主页

https://github.com/openargus/argus

## 许可证

GPL-3.0-or-later

## 构建说明

- 使用 autotools (configure + make) 构建
- 需要静态链接 (R26 终端工具规则)
- 鸿蒙平台需要替换 config.guess/config.sub 和修补 configure 脚本
- 使用 `-j1` 编译（鸿蒙不支持 mkfifo jobserver）
