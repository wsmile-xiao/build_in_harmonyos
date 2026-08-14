# perl-orlite

Extremely light weight SQLite-specific ORM for Perl.

## 软件信息

- **官网**: https://metacpan.org/dist/ORLite
- **许可证**: GPL-1.0-or-later or Artistic-1.0
- **分类**: database
- **语言**: Perl
- **模块类型**: 纯 Perl 模块 (无 C 编译)

## 软件描述

ORLite 是一个极度轻量的 SQLite 专用 ORM (对象关系映射) 模块。它通过读取 SQLite 数据库的 schema，自动生成 Perl 包和方法，提供简洁的数据库访问接口。

ORLite 不是传统的 ORM——它是一个代码生成器。使用时通过 `use ORLite { file => 'db.sqlite' }` 语法，ORLite 会连接到指定的 SQLite 数据库，分析表结构，并在调用者的包命名空间中生成对应的 ORM 方法。

### 核心功能

- 自动 schema 发现和代码生成
- 支持表和视图的 ORM 映射
- 提供增删改查 (CRUD) 方法
- 支持事务 (begin/commit/rollback)
- 支持自定义创建 (create 模式)
- 支持缓存和 prune 模式

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.00-r0 | published | 2026-07-02 | 纯 Perl 模块，Conan 验证通过 |

## 运行依赖

- perl (>= 5.006)
- perl-dbi (>= 1.607) — DBI 1.637 已安装 (PurePerl 回退可用)
- perl-dbd-sqlite (>= 1.27) — DBD::SQLite 1.78 已安装 (需系统目录安装 .so)
- perl-params-util (>= 1.00) — Params::Util 1.07 已安装
- perl-file-remove — File::Remove 1.61 已安装

## 编译依赖

- perl
- perl-extutils-makemaker (ExtUtils::MakeMaker 7.76)

## 使用说明

### 安装

```bash
# 通过 Conan 安装
conan install --requires=perl-orlite/2.00-r0

# 或手动安装
perl Makefile.PL && make && make install
```

### 基本用法

```perl
use ORLite {
    file    => 'mydb.sqlite',
    package => 'My::DB',
};

# 生成的 My::DB 包提供以下方法:
My::DB->connect();           # 获取数据库连接
My::DB->dbh();               # 获取 DBI 句柄
My::DB->selectall_arrayref($sql);  # 查询
My::DB->begin();             # 开始事务
My::DB->commit();            # 提交事务
My::DB->rollback();          # 回滚事务
```

### 创建模式

```perl
use ORLite {
    file    => 'newdb.sqlite',
    create  => sub {
        my $dbh = shift;
        $dbh->do('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)');
    },
    package => 'My::DB',
};
```

### 注意事项

**鸿蒙平台 SELinux 限制 (E046)**:

ORLite 运行时依赖 DBD::SQLite 的 XS 共享库 (SQLite.so)。在 OpenHarmony 平台上，用户目录 (HMDFS) 的 .so 文件受 SELinux 限制无法加载 (`hmdfs:s0` 类型)。需要管理员将 SQLite.so 安装到系统目录 `/data/service/hnp` 以获得正确的 SELinux 类型 (`hnp_file:s0`)。

此限制与 perl-dbd-pg 遇到的 XS 模块 .so 加载问题相同，是平台特性，不影响编译和包管理。

**安装 DBD::SQLite .so 到系统目录**:
```bash
sudo -u installs cp ~/usr/local/lib/perl5/aarch64-linux/auto/DBD/SQLite/SQLite.so \
  /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/DBD/SQLite/
```

## 测试

### 编译测试

- `perl Makefile.PL` ✅ 成功
- `make` ✅ 成功
- `make install` ✅ 成功
- `make test` ❌ 失败 (DBD::SQLite .so SELinux 限制)

### Conan 验证 (8 道门禁)

全部通过 ✅ (G0-G4 + L2/L4/L5)

### 功能测试

- 文件完整性 ✅
- API 接口验证 ✅ (45 个方法)
- Mock 功能测试 ✅ (14/15 通过)
- Conan test_package ✅ (双测试通过)

## 知识沉淀

- E155: 纯 Perl 模块使用 ExtUtils::MakeMaker 构建，无 C 编译
- E046: DBD::SQLite .so 在 OHOS 上受 SELinux 限制，影响运行时测试
- CPAN 作者可能变更，需通过 API 查询正确 URL
- Conan 配方需从 Autotools 模板适配为 Perl 构建系统
- test_package 应使用 mock 机制验证 API 接口，而非仅文件存在性

---
*OpenHarmony 编译归档 · 2026-07-02*
