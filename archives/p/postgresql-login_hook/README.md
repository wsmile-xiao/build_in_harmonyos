# postgresql-login_hook

PostgreSQL 扩展，用于模拟登录触发器功能。

## 描述

login_hook 是一个 PostgreSQL 扩展，允许在用户登录时执行自定义函数。主要用于：
- 实现登录审计
- 执行登录时的自定义逻辑
- 模拟 Oracle 登录触发器功能

## 来源

- 项目地址: https://github.com/splendiddata/login_hook
- 作者: Splendid Data Product Development B.V.
- 许可证: GPL v3

## 版本

- 1.5 (2026-06-02): 支持 PostgreSQL 17

## 编译说明

- 构建系统: PGXS (PostgreSQL Extension Building Infrastructure)
- 依赖: PostgreSQL 17+
- 补丁: PostgreSQL 17 API 适配（IsBackgroundWorker → AmBackgroundWorkerProcess）

## 安装

```sql
CREATE EXTENSION login_hook;
```

## 相关软件

- PostgreSQL: 数据库核心
- pg_cron: 定时任务扩展
- pg_partman: 分区管理扩展