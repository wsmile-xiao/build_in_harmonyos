# perl-sql-abstract

Generate SQL from Perl data structures.

## 软件信息

- **官网**: https://metacpan.org/dist/SQL-Abstract
- **许可证**: perl_5 (Artistic License 2.0 或 GPL v1+)
- **分类**: database

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.000001 | published | 2026-07-03 | 纯 Perl 模块，编译+测试通过，conan-verify 全部 PASS |

## 运行依赖

- perl
- perl-moo
- perl-sub-quote
- perl-hash-merge
- perl-mro-compat
- perl-text-balanced

## 编译依赖

- perl

## 使用说明

SQL::Abstract 是一个 Perl 模块，用于从 Perl 数据结构生成 SQL 语句。支持 SELECT、INSERT、UPDATE、DELETE 等 SQL 语句的生成，以及 WHERE 子句的复杂条件构建。

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-sql-abstract/2.000001
```

安装后设置 PERL5LIB 环境变量指向模块的 `lib/perl5` 目录即可使用。

### 基本用法

```perl
use SQL::Abstract;

my $sqla = SQL::Abstract->new;

# 生成 WHERE 子句
my ($sql, @bind) = $sqla->where({ name => 'John', age => { '>=' => 18 } });
# $sql = "WHERE ( age >= ? AND name = ? )"
# @bind = ('18', 'John')

# 生成 SELECT 语句
my ($sql, @bind) = $sqla->select('users', '*', { name => 'Jane' });

# 生成 INSERT 语句
my ($sql, @bind) = $sqla->insert('users', { name => 'Bob', age => 25 });

# 生成 UPDATE 语句
my ($sql, @bind) = $sqla->update('users', { age => 26 }, { name => 'Bob' });

# 生成 DELETE 语句
my ($sql, @bind) = $sqla->delete('users', { name => 'Bob' });
```

### 注意事项

- 这是纯 Perl 模块，不需要 C 编译器
- 需要正确设置 PERL5LIB 环境变量包含模块路径
- 运行时依赖（perl-moo 等）需提前安装

---
*OpenHarmony 编译归档 · 2026-07-03*
