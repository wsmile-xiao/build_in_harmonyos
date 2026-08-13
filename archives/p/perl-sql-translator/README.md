# perl-sql-translator

SQL::Translator — Perl module for SQL DDL transformations (parsing, translating, and producing SQL schemas).

## 软件信息

- **官网**: https://metacpan.org/release/SQL-Translator
- **许可证**: GPL-1.0-or-later OR Artistic-1.0
- **分类**: database
- **构建系统**: Perl ExtUtils::MakeMaker (Makefile.PL)

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.66-r0 | built | 2026-07-03 | 纯 Perl 模块，功能测试 21/21 通过 (100%) |

## 运行依赖

- perl 5.42.0
- Moo, Parse::RecDescent, Try::Tiny, Sub::Quote, Package::Variant, File::ShareDir
- YAML::Tiny (作为 YAML 后端)
- JSON::PP (Perl 核心模块，通过 JSON::MaybeXS 桩)
- DBI (纯 Perl 桩，仅 SQL 类型常量)

## 功能支持

### 转换路径（全部通过测试）
- MySQL ↔ PostgreSQL ✅
- MySQL ↔ SQLite ✅
- PostgreSQL → MySQL ✅
- SQLServer → PostgreSQL ✅
- 任意格式 → YAML 序列化 ✅
- YAML → 任意格式反序列化 ✅
- 任意格式 → JSON 序列化 ✅

### 支持的 schema 元素
- 表定义 (CREATE TABLE) ✅
- 主键 (PRIMARY KEY) ✅
- 外键 (FOREIGN KEY, ON DELETE CASCADE) ✅
- 索引 (CREATE INDEX) ✅
- 唯一约束 (UNIQUE) ✅
- 数据类型映射 (AUTO_INCREMENT→serial, TEXT→text 等) ✅

### 命令行工具
- `sqlt` — 主转换工具
- `sqlt-diagram` — 数据库关系图
- `sqlt-diff` — Schema 差异比较
- `sqlt-dumper` — 数据导出
- `sqlt-graph` — 图形化 schema

### 解析器
MySQL, PostgreSQL, SQLite, SQLServer, YAML, JSON, Oracle, Sybase, DB2, Storable, xSV, XML, DBI (模块加载通过，实际 DB 连接不可用)

### 生产器
PostgreSQL, MySQL, SQLite, YAML, JSON, Oracle, Sybase, DB2, ClassDBI

## 平台适配

### 创建的桩模块

| 模块 | 替代 | 原因 |
|------|------|------|
| DBI.pm (纯 Perl) | DBI XS .so | SELinux HMDFS 阻止 .so 加载 |
| YAML.pm (包装器) | YAML 模块 | 系统 Perl 未安装 |
| JSON/MaybeXS.pm (纯 Perl) | JSON::MaybeXS | 委托 JSON::PP (Perl 核心模块) |

### 唯一平台限制

DBI `connect()`（实际连接数据库查询 schema）不可用，因为需要 DBI XS .so 运行时加载。此限制**不影响**任何文件级 SQL DDL 转换功能。

## 使用方法

```bash
# 设置环境变量
export PERL5LIB=/storage/Users/currentUser/usr/local/perl5/lib/perl5:/storage/Users/currentUser/usr/local/perl5/lib/perl5/aarch64-linux

# MySQL -> PostgreSQL
sqlt --from MySQL --to PostgreSQL input.sql

# MySQL -> SQLite
sqlt --from MySQL --to SQLite input.sql

# MySQL -> JSON
sqlt --from MySQL --to JSON input.sql

# MySQL -> YAML (序列化)
sqlt --from MySQL --to YAML input.sql > schema.yml

# YAML -> PostgreSQL (反序列化)
sqlt --from YAML --to PostgreSQL schema.yml

# SQLServer -> PostgreSQL (注意: 需要 dbo.table 格式)
sqlt --from SQLServer --to PostgreSQL input.sql
```

---
*OpenHarmony 编译归档 · 2026-07-03*
