# logcli

> Loki 的命令行查询工具

## 简介

logcli 是 Grafana Loki 的命令行客户端，用于查询和分析日志数据。Loki 是一个受 Prometheus 启发的日志聚合系统，设计成本效益高且易于操作。

## 特性

- 支持 LogQL 查询语言
- 支持标签过滤和指标查询
- 支持实时日志流跟踪
- 输出格式可选（JSON、文本等）

## 已编译版本

- 3.7.2 (2026-05-28)

## 功能验证

```bash
logcli --version
```

## 参考

- [Grafana Loki 文档](https://grafana.com/docs/loki/)
- [源码仓库](https://github.com/grafana/loki)