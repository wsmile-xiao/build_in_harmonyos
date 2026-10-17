# cyrus-sasl-sql — Cyrus SASL SQL auxprop 插件包

## 简介

cyrus-sasl-sql 是 Cyrus SASL 的 **SQL auxprop 插件**包：与 `cyrus-sasl` 同源
（上游 2.1.28 发布包），以 `--enable-sql --with-sqlite3` 构建，把 SQL 辅助属性
（auxiliary property）后端**静态链入** `libsasl2`。

与族内其它包（`cyrus-sasl-login`、`cyrus-sasl-gs2` 等适配**认证机制**）不同，
本包适配的是 **auxprop 插件**：它不参与 SASL 机制协商，而是在服务端为
`auxprop_plugin: sql` 提供用户密码/属性的数据库查询能力（典型场景：SMTP/IMAP
服务把账号密码存在数据库里，而非 sasldb 文件）。

SQL auxprop 支持 4 个后端（`plugins/sql.c` 内以 `HAVE_MYSQL` / `HAVE_PGSQL` /
`HAVE_SQLITE` / `HAVE_SQLITE3` 编译期门控）：

| 后端 | 本包 | 说明 |
|------|------|------|
| **SQLite3** | ✅ **启用** | 内嵌、无服务器，CI 可真实初始化验证 |
| SQLite | ❌ 关闭 | v2 旧 API |
| MySQL | ❌ 关闭 | 需运行期数据库服务，无法在 CI 端到端验证 |
| PostgreSQL | ❌ 关闭 | 同上 |

上游语法要求 `--enable-sql` 时四者**至少其一**，否则 configure 直接
`AC_MSG_ERROR` 失败——本包以 SQLite3 满足该约束。

## OpenHarmony 适配要点

- **构建系统**: Autotools（configure + make，in-source 构建）
- **静态链入而非 dlopen**: 上游提供 `STATIC_SQL`（`configure.ac` 的
  `AC_DEFINE(STATIC_SQL,...)`，`lib/staticopen.h:126/181` 已注册
  `SPECIFIC_AUXPROP_PLUG_INIT(sql, "SQL")`），因此 SQL 后端随 `libsasl2` 静态
  交付，**不依赖运行期插件搜索路径**（族内 GS2 因上游无 `STATIC_GS2` 只能走共享
  插件，本包无此限制）
- **SQLite3 依赖**: `sqlite3/3.53.4`，configure 以 `--with-sqlite3=<prefix>` 指向
  Conan 包（configure 会检查 `<prefix>/lib/libsqlite3.a` 并追加 `-lsqlite3` 与
  `-I<prefix>/include`）
- **构建编译器探测**: configure 用 `AC_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc`，OHOS 仅有
  clang，需显式喂 `CC_FOR_BUILD=clang`（族内先例）
- **HMDFS 临时目录**: TMPDIR 指到源码树内 `tmp`，并沿用 configure 补丁把
  `umask 077` 放宽为 `umask 022`
- **install 脚本**: OHOS 无 coreutils `install`，经 `MKDIR_P/INSTALL/INSTALL_PROGRAM/
  INSTALL_DATA` 变量注入随包的 `config/install-sh`
- **其余后端全关**: `--without-mysql --without-pgsql --without-sqlite`，
  `--with-dblib=none`，mechanism 侧维持族内基线（login/ntlm/otp/srp/ldapdb/gssapi
  等全关）

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.28 | built | 2026-09-13 | SQL/SQLite3 auxprop 首个适配版本，待真机验证 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cyrus-sasl-sql 2.1.28
```

## 使用方法

SQL auxprop 通过 SASL 配置启用。以服务端为例（`/etc/sasl2/<service>.conf`）：

```
auxprop_plugin: sql
sql_engine: sqlite3
sql_hostnames: /var/lib/sasl/sasldb.sqlite
sql_database: sasldb
sql_user: user
sql_passwd: password
sql_select: SELECT password, NULL AS userdata FROM users WHERE username = '%u'
```

C 侧初始化并确认 SQL 插件已注册：

```c
#include <sasl/sasl.h>

sasl_server_init(NULL, "myapp");   /* SQL 静态链入，无需设置 SASL_PATH */

const char *mechs = NULL;
unsigned mechs_len = 0;
sasl_listmech(conn, "user", "", " ", "", &mechs, &mechs_len, NULL);
/* auxprop 的生效需配置 auxprop_plugin: sql —— 见 test_package 的初始化验证 */
```

## 说明

本包 `test_package` 验证 **SQL auxprop 插件被真实注册并加载**：以
`auxprop_plugin: sql` + `sql_engine: sqlite3` 配置运行
`sasl_server_init()` / `sasl_auxprop_request()`，并断言不返回
"no auxprop plugin" 类错误。完整认证链路还需数据库表结构与应用侧配置，
不在包级消费者测试范围内。
