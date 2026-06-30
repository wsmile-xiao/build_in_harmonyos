# chronograf

**分类**: monitoring (监控工具)

## 简介

chronograf 是 InfluxData 开发的时间序列数据可视化工具，是 TICK 技术栈（Telegraf、InfluxDB、Chronograf、Kapacitor）的重要组成部分。

主要功能：
- 可视化时间序列数据
- 监控仪表板创建和管理
- 数据探索和查询
- 与 InfluxDB 和 Kapacitor 集成
- 基础设施监控

## 官方资源

- **主页**: https://www.influxdata.com/time-series-platform/chronograf/
- **源码**: https://github.com/influxdata/chronograf
- **许可证**: MIT

## OpenHarmony 适配说明

### 构建系统

**类型**: prebuilt（预编译二进制）

chronograf 是 Go 语言编写，官方提供预编译 ARM64 二进制包，无需从源码编译。

### 适配要点

1. **ELF 签名**：预编译二进制需要使用 `ohc-run.py sign-elf` 进行签名，否则无法在 OpenHarmony 上执行
2. **安全授权**：首次运行时系统会弹出安全授权窗口，用户需手动确认
3. **静态链接**：二进制为静态链接，无外部库依赖

### 已编译版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 1.11.3 | published | 2026-06-05 | 预编译 ARM64 包，已签名 |

## 使用说明

安装后执行：
```bash
chronograf --version
```

首次运行需要安全弹窗授权。

## 相关工具

- **telegraf**: 数据采集代理
- **influxdb**: 时间序列数据库
- **kapacitor**: 数据处理引擎
- **chronoctl**: chronograf 命令行工具（包含在预编译包中）