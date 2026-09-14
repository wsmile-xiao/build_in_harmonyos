# mysql-client

MySQL 8.0 客户端工具集与 libmysqlclient 客户端库（HarmonyOS PC 适配）。

提供 `mysql` 交互式客户端、`mysqladmin`、`mysqldump`、`mysqlcheck`、
`mysqlimport`、`mysqlshow`、`mysqlslap` 等客户端工具，以及静态客户端库
`libmysqlclient.a`（client-only 构建，不含 mysqld 服务器）。

## OHOS 适配要点

- client-only 子集构建（`WITHOUT_SERVER=ON`），CMake 单仓交叉编译。
- OHOS 目标以 `CMAKE_SYSTEM_NAME=Linux` + `aarch64` + `OHOS=1` 交叉配置。
- OHOS libc 无 pthread_cancel / libresolv 等，差异见各版本 notes.md 与 patches/。
- 依赖：openssl、zlib、ncurses、boost（均为 Conan 制品仓预编译包）。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 8.0.46 | built | maintenance 系最新 GA，配方复刻自已发布的 mysql/8.0.46（同 tarball） |

## 参照

- archives/m/mysql/8.0.46（同源码母版，published）
- archives/p/percona-server/8.4.10_10（8.4 系参照）
- knowledge E459
