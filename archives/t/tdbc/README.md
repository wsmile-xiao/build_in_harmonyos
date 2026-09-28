# tdbc

**TDBC (Tcl Database Connectivity)** — Tcl 的数据库连接接口标准的基础包。

- 上游：<https://core.tcl-lang.org/tdbc/>
- 版本：1.1.14
- 构建系统：autotools（TEA — Tcl Extension Architecture）
- 依赖：`tcl/8.6.16`（build + run）

## 说明

本包提供 TDBC 的**基类与 SQL 分词器**（`generic/tdbc.c`、`generic/tdbcTokenize.c`、
`library/tdbc.tcl`），本身不连接任何数据库；具体数据库访问由独立驱动包提供：

| 驱动包 | 数据库客户端依赖 |
|--------|-----------------|
| tdbcmysql | mysql-client |
| tdbcodbc | unixodbc |
| tdbcpostgres | libpq |
| tdbcsqlite3 | sqlite3 |

## 产物

| 路径 | 说明 |
|------|------|
| `lib/tdbc1.1.14/libtdbc1.1.14.so` | Tcl 扩展共享库（tclsh 经 `pkgIndex.tcl` dlopen） |
| `lib/tdbc1.1.14/libtdbcstub1.1.14.a` | stub 静态库（C 扩展链接用） |
| `lib/tdbc1.1.14/{pkgIndex.tcl,tdbc.tcl,tdbcConfig.sh}` | Tcl 包索引 / 基类脚本 / 构建配置 |
| `include/tdbc*.h` | 公共与内部头文件 |
| `share/man/{man3,mann}/*` | 参考手册 |

## 使用

```tcl
package require tdbc 1.1.14
tdbc::tokenize {SELECT * FROM t WHERE a = :b}
```
