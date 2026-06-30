# perl-mojo-pg

## 简介
Mojo::Pg - Mojo 的 PostgreSQL 数据库驱动模块，提供异步和同步数据库操作、连接池管理、数据库迁移、发布/订阅等功能。基于 Mojolicious 框架，使用 SQL::Abstract::Pg 生成 PostgreSQL 特有的 SQL 语句。

## OHOS 适配
- 纯 Perl 模块（无 C/XS 代码），构建仅复制 .pm 文件
- 使用 MakeMaker (Makefile.PL) 构建系统，INSTALL_BASE 指定用户目录
- 无需源码补丁
- 运行时依赖 DBD::Pg 的 XS .so 文件需安装到系统目录 /data/service/hnp/（SELinux 要求）

## 依赖
- perl >= 5.016
- Mojolicious >= 8.50 (实际安装: 9.42)
- DBI >= 1.614 (实际安装: 1.637, PurePerl 模式)
- DBD::Pg >= 3.007004 (实际安装: 3.18.0, XS 加载需系统目录)
- SQL::Abstract >= 2.0 (实际安装: 2.000001)
- SQL::Abstract::Pg >= 1.0 (实际安装: 1.0)

## 功能验证
```bash
# 模块加载
perl -MMojo::Pg -e 'print "Mojo::Pg version: $Mojo::Pg::VERSION\n"'

# SQL 生成功能
perl -MSQL::Abstract::Pg -e '
my $sql = SQL::Abstract::Pg->new;
my ($stmt, @bind) = $sql->insert("users", {name => "test"}, {returning => "id"});
print "$stmt\n";
'
# 输出: INSERT INTO users (name) VALUES (?) RETURNING id

# Connection 解析测试
cd /path/to/Mojo-Pg-4.28
perl t/connection.t
```

## 已知限制
1. DBD::Pg XS .so 文件在 HMDFS 上无法 dlopen (SELinux 限制)，需管理员安装到系统目录
2. DBI 在 PurePerl 模式下运行 (性能略低)
3. 在线测试需要 PostgreSQL 服务端 (当前环境未安装)

## 参考
- CPAN: https://metacpan.org/pod/Mojo::Pg
- GitHub: https://github.com/mojolicious/mojo-pg
