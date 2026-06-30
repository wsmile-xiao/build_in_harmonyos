# prometheus

> Prometheus — 开源监控和告警系统

## 简介

Prometheus 是一个开源的系统监控和告警工具包。它通过 HTTP 主动拉取指标数据，支持多维度数据模型和强大的查询语言 PromQL。Prometheus 广泛应用于云原生和容器化环境的监控。

## OHOS 适配要点

- Go 项目，因 Go runtime 内部冲突和 HMDFS 限制无法本地编译
- 使用官方预编译 linux-arm64 二进制 + sign-elf 签名适配
- prometheus 和 promtool 两个二进制都需要 ELF 签名

## 排除与替代

- 本地 Go 编编译因 runtime 内部冲突（Swiss table vs 传统实现）和 HMDFS 限制失败
- 使用官方预编译二进制替代

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| goenv | 3.1.1 | Go 版本管理（编译尝试） |

## 功能验证

```bash
prometheus --version
promtool --help
```

## 参考

- [官方文档](https://prometheus.io/docs/)
- [源码仓库](https://github.com/prometheus/prometheus)
