# pg_partman v5.4.3 — OpenHarmony 预编译包

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | pg_partman |
| 版本 | 5.4.3 |
| 许可证 | PostgreSQL |
| 目标平台 | aarch64-unknown-linux-ohos (OpenHarmony) |
| 构建系统 | PGXS (PostgreSQL Extension Building Infrastructure) |
| 构建日期 | 2026-06-02 |

## 简介

pg_partman 是 PostgreSQL 的分区管理扩展，支持按时间或 ID 自动创建和管理表分区。它提供后台工作进程自动维护分区，以及丰富的 SQL 函数和过程进行分区操作。

## 预编译包内容

### 共享库
- `lib/postgresql/pg_partman_bgw.so` — 后台工作进程 C 模块 (30KB)
  - ELF64 AArch64, OHOS 签名已嵌入
  - 仅依赖 libc.so

### 扩展定义
- `share/postgresql/extension/pg_partman.control` — 扩展控制文件
- `share/postgresql/extension/pg_partman--5.4.3.sql` — 主 SQL 定义 (7650行)
- `share/postgresql/extension/pg_partman--X--Y.sql` — 100 个增量升级脚本

### 文档
- `share/doc/postgresql/extension/pg_partman.md` — 使用手册
- 其他文档文件

## 安装方法

```sql
-- 在 PostgreSQL 中执行
CREATE EXTENSION pg_partman;
```

需要 PostgreSQL >= 14 且已安装 plpgsql 扩展。

## 运行时依赖

- PostgreSQL >= 14 (提供 SPI、BackgroundWorker 等 API)
- plpgsql 扩展
- libc.so (系统库)

## 构建依赖

- PostgreSQL 16.4 (提供 pg_config 和 PGXS 构建基础设施)
- clang (OpenHarmony NDK 编译器)

## 测试说明

- 编译产物验证: 14/14 通过 (ELF 头、签名、符号、SQL完整性等)
- 回归测试: 跳过 (需要 PostgreSQL 服务器运行时环境)
- 建议在部署环境中运行 `make installcheck` 验证功能

## sha256 校验和

```
pg_partman_bgw.so:       65e66c51fd7564947c5fda401750e23522593ad9a6c5bef5a38117e99d1e106f
pg_partman--5.4.3.sql:   02a0a22b59d7486c5339c0768c9c64e74f5d1c729e4ca84911395d3ea5d9bd4d
pg_partman.control:      6ede9333f13f773fea3834d4460aff53e25955315010c77509cefd049eb942c4
```