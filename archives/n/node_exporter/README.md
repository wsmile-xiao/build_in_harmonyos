# node_exporter for HarmonyOS/OpenHarmony

> **编译日期**: 2026-06-05
> **状态**: ✅ built — 编译通过 + 预编译包就绪
> **构建系统**: Go (go build)

## 软件简介

node_exporter 是 Prometheus 官方提供的机器级指标导出器，用于采集服务器的硬件和操作系统指标（CPU、内存、磁盘、网络等），通过 HTTP 接口暴露给 Prometheus 采集。

**为什么鸿蒙需要它？** 鸿蒙系统运维监控需要 Prometheus 生态工具，node_exporter 是标准采集端。

## OHOS 适配说明

- Go 语言项目，使用 `go build` 编译，无需传统 configure/make 流程
- 纯 Go 实现，零外部 C 依赖（仅依赖 musl libc 运行时）
- 需适配 Go 交叉编译目标：`GOOS=linux GOARCH=arm64`

## 依赖关系

### 编译依赖
- Go >= 1.22

### 运行依赖
- musl libc (系统自带)

## 参考资料

- **官网**: https://prometheus.io
- **源码仓库**: https://github.com/prometheus/node_exporter
- **Release**: https://github.com/prometheus/node_exporter/releases

## 版本历史

- **1.11.1** (2026-06-05): Built for OpenHarmony