# TimescaleDB

## 简介
TimescaleDB 是一个 PostgreSQL 扩展，专为时序数据和事件数据提供高性能实时分析能力。它将标准 PostgreSQL 转换为时序数据库，支持快速插入、复杂查询和数据压缩。

## OHOS 适配要点

### 版本兼容性
- TimescaleDB 2.27.2 官方要求 PostgreSQL 17.2+
- 当前 OHOS 环境为 PostgreSQL 17.0，需要使用 EXPERIMENTAL=ON 绕过版本检查
- PG17.0 缺少部分 PG17.1+ 引入的 API（如 ri_needLockTagTuple），需要补丁适配

### 构建系统适配
- CMake 构建系统
- 需要从 pg_config 的 CPPFLAGS 提取 OpenSSL include 路径
- Bootstrap 阶段使用 `./bootstrap -DEXPERIMENTAL=ON`

### 已知问题
1. PostgreSQL API 不兼容：ri_needLockTagTuple 和 InplaceUpdateTupleLock 在 PG17.1+ 才引入
2. OpenSSL 头文件路径：CMakeLists.txt 默认不处理 pg_config 的 CPPFLAGS

## 依赖
- PostgreSQL 17.0+（编译和运行时）
- OpenSSL（编译时）

## 功能验证
安装后需要在 PostgreSQL 中创建扩展：
```sql
CREATE EXTENSION timescaledb;
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';
```

## 参考
- 官网：https://www.timescale.com/
- GitHub：https://github.com/timescale/timescaledb
- 文档：https://docs.timescale.com/
