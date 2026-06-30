# postgresql-mysql_fdw REL-2_9_3 适配笔记

## 编译环境
- 构建系统: pgxs (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `init-build postgresql-mysql_fdw REL-2_9_3 --url=https://api.github.com/repos/EnterpriseDB/mysql_fdw/tarball/REL-2_9_3`
2. 安装依赖 mariadb-connector-c 3.4.8（预编译包）+ 创建 mysql_config → mariadb_config 符号链接
3. 修改 Makefile 增加 mariadb 库名检测逻辑
4. 修改 mysql_fdw.c 添加 `__OHOS__` 平台守卫（RTLD_DEEPBIND 不可用）
5. `make USE_PGXS=1` 编译
6. `make USE_PGXS=1 install DESTDIR=$TEST_PREFIX` staging 安装
7. Staging 验证 + 打包 + make install + 用户验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | RTLD_DEEPBIND 未声明 | OpenHarmony musl libc 不支持 RTLD_DEEPBIND | 在 mysql_fdw.c 的 dlopen 平台守卫中添加 `__OHOS__` 条件，使用 RTLD_LAZY 代替 RTLD_LAZY|RTLD_DEEPBIND |
| 2 | _MYSQL_LIBNAME=libmysqlclient.so | mariadb-connector-c 提供 libmariadb.so 而非 libmysqlclient.so | 修改 Makefile 增加对 mariadb（不含 client 后缀）的检测，将 MYSQL_LIB 设为 mariadb |
| 3 | mysql_config 不存在 | mariadb-connector-c 只提供 mariadb_config | 创建 mysql_config → mariadb_config 符号链接 |

## 源码修改

- Makefile: 增加 `else ifneq ($(findstring mariadb,$(LIB)),)` 检测 mariadb-connector-c 提供的 libmariadb
- mysql_fdw.c: 将 `#if defined(__APPLE__) || defined(__FreeBSD__)` 改为 `#if defined(__APPLE__) || defined(__FreeBSD__) || defined(__OHOS__)`

## 依赖版本

- PostgreSQL 17.10（已安装）
- mariadb-connector-c 3.4.8（预编译包安装）

## 验证结果

```bash
$ file ~/usr/local/lib/postgresql/mysql_fdw.so
ELF shared object, 64-bit LSB arm64, not stripped
$ readelf -d mysql_fdw.so | grep RUNPATH
Library runpath: [/storage/Users/currentUser/usr/local/lib]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-mysql_fdw-REL-2_9_3-ohos-aarch64.tar.gz | 117KB | 预编译包（stripped） |
| postgresql-mysql_fdw-REL-2_9_3-ohos-aarch64-debug.tar.gz | 382KB | 调试符号包 |

## 注意事项

- mysql_fdw 是 PostgreSQL FDW 扩展，测试需要运行 PostgreSQL 和 MySQL 服务器，编译环境无法执行 installcheck
- 需要先安装 PostgreSQL 和 mariadb-connector-c 预编译包才能使用
- mysql_config 是 mariadb_config 的符号链接，部署时也需要
---

**编译结束**: 2026-06-10 22:21
**最终状态**: published
