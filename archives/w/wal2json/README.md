# wal2json

wal2json 是 PostgreSQL 逻辑解码输出插件，将 WAL (Write-Ahead Log) 变更集转换为 JSON 格式输出。支持 INSERT、UPDATE、DELETE、TRUNCATE 操作，以及事务级变更输出和逻辑解码消息传递。

## 功能概述

- **格式版本 1**: 每个 JSON 对象包含一个事务的所有变更
- **格式版本 2**: 每个变更生成一个独立的 JSON 对象
- 支持可选输出: 时间戳、LSN、事务 ID、schema、数据类型、主键等
- 支持表过滤 (`filter-tables`, `add-tables`) 和消息过滤 (`filter-msg-prefixes`)
- 支持 numeric 数据类型以字符串形式输出（避免 JSON Infinity/NaN 问题）

## OHOS 适配要点

- **构建系统**: PGXS (PostgreSQL Extension Building Infrastructure)，需要 `pg_config` 和 PostgreSQL server 开发头文件
- **依赖缺失**: cmd-pkgs 无 PostgreSQL 预编译包，需从 PostgreSQL 源码获取头文件
- **pg_config**: 创建最小 pg_config wrapper 脚本，指向 PostgreSQL 源码树 `src/include/`
- **E097 限制**: PostgreSQL config.status 在 HMDFS 上无法创建临时文件，需 Python 脚本手动处理 .in 模板
- **类型定义**: aarch64 上 `PG_INT64_TYPE` 应为 `long int`（long=8字节），不可使用 `long long int`
- **测试限制**: 回归测试需要 PostgreSQL 服务器运行（`wal_level=logical`），交叉编译环境无法执行

## 编译步骤 (OHOS)

```bash
# 1. 准备 PostgreSQL 源码头文件
#    下载 PostgreSQL 16.4 源码，补丁 config.guess/config.sub (E007)
#    手动处理 config.status .in 模板 (E097)
#    创建 pg_config wrapper 脚本

# 2. 编译 wal2json.so
PGSRC="/path/to/postgresql-16.4.src"
PREFIX="/storage/Users/currentUser/usr/local"

clang -fPIC -O2 -Wall -Wmissing-prototypes -Wpointer-arith \
  -Wdeclaration-after-statement -Wformat-security \
  -fno-strict-aliasing -fwrapv -Wno-unused-command-line-argument \
  -I. -I$PGSRC/src/include -I$PREFIX/include \
  -D_GNU_SOURCE -DHAVE_CONFIG_H \
  -c wal2json.c -o wal2json.o

clang -shared -fPIC -o wal2json.so wal2json.o -lm

# 3. 安装
cp wal2json.so $PREFIX/lib/wal2json.so
```

## 依赖关系

- **编译依赖**: PostgreSQL 开发头文件 (postgres.h, replication/logical.h, utils/builtins.h 等) + pg_config
- **运行依赖**: PostgreSQL 16+ 服务器（需配置 `wal_level = logical`, `max_replication_slots ≥ 1`）
- **系统依赖**: libc.so

## 部署说明

解压预编译包后，将 `lib/wal2json.so` 复制到 PostgreSQL 的 `pkglibdir` 目录（通常为 `$PG_PREFIX/lib/`），然后在 PostgreSQL 中创建逻辑复制槽：

```sql
SELECT pg_create_logical_replication_slot('wal2json_slot', 'wal2json');
```

## 参考资料

- 官网: https://github.com/eulerto/wal2json
- PostgreSQL 逻辑解码: https://www.postgresql.org/docs/current/logicaldecoding.html
- PGXS 扩展开发: https://www.postgresql.org/docs/current/extend-pgxs.html