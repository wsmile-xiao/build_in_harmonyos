# pg_activity

pg_activity 是一个基于终端的 PostgreSQL 服务器活动监控工具，类似于 top/htop 但专为 PostgreSQL 设计。

## 功能概述

- 实时显示 PostgreSQL 查询和进程活动
- 支持按 CPU、内存、IO 等维度排序和筛选
- 提供长时间运行查询的视图
- 支持最小、窄、宽三种显示模式（配置文件）
- 支持查询取消和终止操作

## OHOS 适配

- **构建系统**: Python/setuptools（pyproject.toml），纯 Python 项目
- **无需源码修改**: 无 C 扩展，无平台相关代码
- **pip DESTDIR 问题**: 此平台 pip 不支持 --prefix + --root 同时使用，使用 --target 替代
- **PYTHONPATH**: 系统 Python 3.12 不读取 PYTHONPATH，需创建 .pth 文件添加路径
- **可选依赖**: psycopg/psycopg2 是连接 PostgreSQL 的驱动，为可选运行时依赖，无 aarch64-ohos 二进制 wheel

## 依赖关系

### 编译依赖
- Python >= 3.9
- setuptools >= 77.0.0

### 运行依赖（必需）
- attrs >= 17.4, !=21.1
- blessed >= 1.15.0
- humanize >= 0.5.1, !=4.12.0
- psutil >= 2.0.0

### 运行依赖（可选）
- psycopg >= 3.1 或 psycopg2-binary >= 2.8（PostgreSQL 连接驱动）

## 参考资料

- 官网: https://github.com/dalibo/pg_activity
- 文档: https://pg_activity.readthedocs.io
- 源码: https://github.com/dalibo/pg_activity