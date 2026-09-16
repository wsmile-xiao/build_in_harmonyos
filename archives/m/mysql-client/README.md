# mysql-client

MySQL 客户端工具集与 libmysqlclient 客户端库（HarmonyOS PC 适配）。

提供 `mysql` 交互式客户端、`mysqladmin`、`mysqldump`、`mysqlcheck`、
`mysqlbinlog`、`mysqlimport`、`mysqlshow`、`mysqlslap` 等客户端工具，以及
静态客户端库 `libmysqlclient.a`（client-only 构建，不含 mysqld 服务器）。
当前覆盖 8.0.46 / 8.4.11 / 9.7.1 三个版本。

## OHOS 适配要点

- client-only 子集构建（`WITHOUT_SERVER=ON`），CMake 单仓交叉编译。
- OHOS 目标以 `CMAKE_SYSTEM_NAME=Linux` + `aarch64` + `OHOS=1` 交叉配置。
- OHOS libc 无 pthread_cancel / res_nsearch（res_search 在 libc 内）、无
  libresolv 等，能力探测（HAVE_PTHREAD_CANCEL/HAVE_RES_NSEARCH）门控兼容
  shim，差异见各版本 notes.md 与 patches/。
- 依赖：openssl、zlib、ncurses（均为 Conan 制品仓预编译包）；8.0.46 的 boost
  走 `WITH_BOOST`，8.4.11 用源码树 bundled header（boost_1_84_0），无需独立包。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 8.0.46 | built | maintenance 系最新 GA，配方复刻自已发布的 mysql/8.0.46（同 tarball） |
| 8.4.11 | built | maintenance 8.4 系 client-only 适配 |
| 9.7.1 | built | innovator 系首版，配方复刻自 mysql/8.0.46 |

## 参照

- archives/m/mysql/8.0.46（同源码母版，published）
- archives/m/mysql-client/9.7.1（9.x innovator 系先例，PR #9060 在途）
- archives/m/mysql-8.4/8.4.11（别队服务端形态，历史参照）
- archives/p/percona-server/8.4.10_10（8.4 系参照）
- knowledge E459
