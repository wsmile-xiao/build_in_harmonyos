# libgda

GNU Data Access (GDA) 是一个数据库抽象库，提供统一的 API 来访问多种数据库系统。

## 描述

libgda 提供了：
- 数据库连接抽象层
- SQL 解析和执行
- 数据模型接口
- 多种数据库 Provider 支持（SQLite、PostgreSQL、MySQL 等）

## 编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 6.0.0 | built | 2025-05-21 |

## 依赖

- glib-2.0 >= 2.38
- libxml-2.0
- sqlite3 >= 3.22
- iso-codes
- vala (构建依赖)
