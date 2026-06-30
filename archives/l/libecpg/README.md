# libecpg

PostgreSQL Embedded SQL (ECPG) 预处理器和运行时库。

libecpg 是 PostgreSQL 18.3 中的嵌入式 SQL for C (ECPG) 子系统，提供：
- **ecpg** 预处理器：将嵌入式 SQL 语句转换为 C 代码
- **libecpg** 运行时库：ECPG 核心通信库
- **libpgtypes** 类型库：PostgreSQL 数据类型支持（numeric, date, timestamp, interval）
- **libecpg_compat** 兼容库：Informix ESQL 兼容接口

## 关键依赖

libecpg 运行时依赖 **libpq**（PostgreSQL 客户端连接库），编译时依赖 libpq 头文件。
静态链接还需要 **libpgport** 和 **libpgcommon**（PostgreSQL 内部工具库）。

> ✅ 打包产物 `lib/external/` 已包含 libpq.so.5 + libssl + libcrypto，确保运行时自包含。
> 开发时需先安装 libpq 预编译包获取头文件 (libpq-fe.h) 和链接器名称 (libpq.so)。

## 用户安装流程

1. 安装 libpq 预编译包（提供开发头文件和链接器名称）
2. 安装 libecpg 预编译包（包含 ecpg、库文件及运行时依赖）

## 已编译版本

- **18.3** (2026-06-03) — built ✅ (阻塞问题已修复，符合上库要求)