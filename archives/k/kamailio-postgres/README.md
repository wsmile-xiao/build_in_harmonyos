# kamailio-postgres

Kamailio 的 **db_postgres** 模块：通过 PostgreSQL 客户端库（libpq）为 Kamailio 提供 SQL
数据库连接能力（实现 Kamailio 的数据库 API，供 `db_url` 指向 PostgreSQL 的配置使用）。

## 基本信息

- **版本**: 6.0.6
- **上游**: kamailio 6.0.6（<https://www.kamailio.org>、<https://github.com/kamailio/kamailio>）
- **构建系统**: makefile（kamailio 经典 Makefile 体系）
- **编译日期**: 2026-10-10
- **状态**: built
- **打包产物**: `lib/kamailio/modules/db_postgres.so`
- **依赖**: `libpq/18.6.1`

## 简介

模块 `.so` 由 Kamailio 运行时 `loadmodule "db_postgres.so"` 加载，不作为链接库供消费者使用。
适用于以 PostgreSQL 作为 Kamailio 配置库/运行时库的场景（配合 `kamailio-db` 包中的
db 上层模块使用）。

## 已编译版本

| 版本 | 状态 | 预编译包 | 补丁数 |
|------|------|----------|--------|
| 6.0.6 | built | ❌ | 0 |

## OHOS 适配要点

### libpq 探测分支必须钉死
`src/modules/db_postgres/Makefile` 依次尝试 `pkg-config --exists libpq`、
`PGCFG=$(shell which pg_config)`、`LOCALBASE/SYSBASE` 回退。命中系统 pkg-config/pg_config
会注入宿主 include/lib 路径。本配方显式传 `LIBPQ_BUILDER=` 与 `PGCFG=`（make 命令行变量
优先级高于 Makefile 内部赋值）钉死回退分支，并以 `LOCALBASE=<libpq package_folder>`
提供正确路径，另用 `CPATH`/`LIBRARY_PATH` 兜住头/库搜索。

### 构建顺序
必须先 `make cfg include_modules=db_postgres`（生成 `src/config.mak`），再
`make modules modules=modules/db_postgres`；否则报 `No rule to make target 'cfg-defs'`。

### 产物形态
交叉编译产物无 RPATH/RUNPATH，动态依赖仅 `libpq.so.5` + `libc.so`，并带
`FLAGS_1=DF_1_NOW`（模块自身 BIND_NOW）——与 OHOS/musl 加载器无惰性绑定的行为一致，
故 test_package 的 e2e 用例把模块引用的 core 符号以最小 stub 层随测试二进制导出后
再 dlopen，真实走通 `loadmodule` 消费路径。

## 相关模块

同源适配的其它 Kamailio 模块见 `archives/k/kamailio-unixodbc/`（db_unixodbc）、
`archives/k/kamailio-db/`（33 个 DB 上层模块）等。
