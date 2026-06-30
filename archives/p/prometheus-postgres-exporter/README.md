# Prometheus PostgreSQL Exporter

> Prometheus exporter for PostgreSQL server metrics

## 简介

prometheus-postgres-exporter 是一个 Prometheus 导出器，用于采集 PostgreSQL 服务器的指标数据，包括连接数、事务率、缓存命中率、复制状态等，便于通过 Prometheus + Grafana 进行数据库监控。

## OHOS 适配要点

- 编译为静态二进制，避免动态链接依赖
- 无源码修改，使用原生编译流程

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| postgresql | 17+ | 被监控的数据库 |

## 功能验证

```bash
prometheus-postgres-exporter --version
```

## 参考

- [GitHub: prometheus-community/postgres_exporter](https://github.com/prometheus-community/postgres_exporter)
