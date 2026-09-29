# kamailio-unixodbc

Kamailio 的 **db_unixodbc** 模块：通过 unixODBC 驱动管理器为 Kamailio 提供 SQL 数据库连接能力
（实现 Kamailio 的数据库 API，供 `db_url` 指向 unixODBC DSN 的配置使用）。

## 基本信息

- **版本**: 6.0.6
- **上游**: kamailio 6.0.6（<https://www.kamailio.org>）
- **构建系统**: makefile（kamailio 经典 Makefile 体系）
- **编译日期**: 2026-09-25
- **状态**: published
- **打包产物**: `lib/kamailio/modules/db_unixodbc.so`
- **依赖**: `unixodbc/2.3.12`

## 简介

模块 `.so` 由 Kamailio 运行时 `loadmodule "db_unixodbc.so"` 加载，不作为链接库供消费者使用。
适用于需要以 ODBC 数据源（MySQL/PostgreSQL/SQL Server 等）作为 Kamailio 配置库的场景。

## 已编译版本

| 版本 | 状态 | 预编译包 | 补丁数 |
|------|------|----------|--------|
| 6.0.6 | published | ❌ | 0 |

## OHOS 适配要点

### unixODBC 探测分支必须钉死
`src/modules/db_unixodbc/Makefile` 在 `CROSS_COMPILE` 为空时执行 `ODBCCFG=$(shell which odbc_config)`；
命中系统 `odbc_config` 会注入宿主 include/lib 路径。本配方显式传 `ODBCCFG=`（make 命令行变量优先级
高于 Makefile 内部赋值）钉死回退分支，并以 `LOCALBASE=<unixodbc package_folder>` 提供正确路径。

### 构建顺序
必须先 `make cfg include_modules=db_unixodbc`（生成 `src/config.mak`），再
`make modules modules=modules/db_unixodbc`；否则报 `No rule to make target 'cfg-defs'`。

### 产物形态
交叉编译产物无 RPATH/RUNPATH，动态依赖仅 `libodbc.so.2` + `libc.so`（依赖链由 Conan 管理）。

## 相关模块

同源适配的其它 Kamailio 模块见 `archives/k/kamailio-snmpstats/`（snmpstats 模块）。
