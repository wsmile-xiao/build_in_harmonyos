# perl-dbd-pg

Perl DBI driver for PostgreSQL databases.

## 软件信息

- **官网**: https://metacpan.org/pod/DBD::Pg
- **源码**: https://github.com/bucardo/dbdpg
- **许可证**: Artistic-2.0
- **分类**: database

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 3.18.0 | built | 2026-06-10 | 首次编译成功 |

## 运行依赖

- perl
- postgresql (libpq)
- perl-dbi

## 编译依赖

- musl (提供标准 C 库头文件)
- postgresql-client (pg_config)
- perl-dbi

## 使用说明

DBD::Pg 是 Perl DBI 接口的 PostgreSQL 驱动模块，用于 Perl 程序连接 PostgreSQL 数据库。

### 安装

预编译包安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/DBD/Pg/` 目录。

### 注意事项

由于 SELinux HMDFS 限制，XS 模块需要安装到系统目录 `/data/service/hnp` 才能正常加载。

---
*OpenHarmony 编译归档 · 2026-06-10*