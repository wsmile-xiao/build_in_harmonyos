# odpi

ODPI-C（Oracle Database Programming Interface for C）是 Oracle 官方提供的 C 语言数据库编程接口库，
为驱动程序和应用程序开发者简化 Oracle 数据库访问。它在 OCI（Oracle Call Interface）之上提供
通用封装层，支持 Python cx_Oracle/oracledb、Node.js node-oracledb、Go Godror 等多种语言的
Oracle 数据库驱动。

## 版本

- 当前版本: 5.6.4

## 构建系统

ODPI-C 使用纯 Makefile（非 autotools），无 configure 脚本。

```bash
# 关键：LDFLAGS=-shared 必须显式传（环境变量会覆盖 Makefile 的 ?= 赋值）
make LDFLAGS="-shared" PREFIX=$PREFIX -j1
make install PREFIX=$PREFIX
```

> **注意**: Makefile 不支持 DESTDIR 变量，install 目标直接写入 `$(PREFIX)/lib`、`$(PREFIX)/include` 等路径。

## 依赖

- 编译依赖: 无（仅系统库 -ldl -lpthread）
- 运行时依赖: Oracle Instant Client (libclntsh.so)

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 5.6.4 | built | 2026-06-17 |
