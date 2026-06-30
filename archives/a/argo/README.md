# argo

Argo Workflows CLI — Kubernetes-native workflow引擎的命令行工具。

## 概述

Argo Workflows 是一个开源的容器原生工作流引擎，用于在 Kubernetes 上编排和运行并行作业。
argo CLI 是其命令行工具，用于创建、提交、监控和管理工作流。

## 已编译版本

- **4.0.5** (2026-06-01) — Go 1.26.3, CGO_ENABLED=0, static build

## 关键信息

- **源码**: https://github.com/argoproj/argo-workflows
- **构建系统**: Go (custom)
- **依赖**: Go ≥ 1.25.7
- **平台**: linux/arm64 (HarmonyOS/OpenHarmony)

## 鸿蒙适配要点

1. Go linker mmap在HMDFS上失败 → 输出到ext2分区
2. 需UI placeholder (ui/dist/app/index.html) 满足go:embed
3. GitHub不可达 → 通过GOPROXY(goproxy.cn)获取源码
