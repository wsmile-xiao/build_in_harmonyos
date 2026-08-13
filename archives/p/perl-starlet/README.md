# perl-starlet

Starlet — a simple, high-performance PSGI/Plack HTTP server.

## 软件信息

- **官网**: https://metacpan.org/dist/Starlet
- **源码**: http://cpan.metacpan.org/authors/id/K/KA/KAZUHO/Starlet-0.31.tar.gz
- **许可证**: Perl (Artistic-1.0 或 GPL-1.0+)
- **分类**: web-server
- **构建系统**: Perl Module::Install (Makefile.PL)

## 已编译版本

| 版本 | 状态 | 编译日期 | 测试日期 | 说明 |
|------|------|---------|---------|------|
| 0.31-r3 | built | 2026-07-03 | 2026-07-06 | 纯Perl模块，HTTP服务器功能测试全部通过 |

## 运行依赖

- perl (5.8.1+)
- Parallel::Prefork (>= 0.17) — 已安装 0.18
- Plack (>= 0.992) — 已安装 1.0054
- Server::Starter (>= 0.06) — 已安装 0.35

## 编译依赖

- perl (已安装于 /data/service/hnp/perl.org/perl_5.42.0/)
- Module::Install (内置于源码 inc/ 目录)

> Starlet 是纯 Perl 模块，不需要 C 编译器。

## 安装产物

安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/` 目录下：

| 文件 | 说明 |
|------|------|
| Starlet.pm | 主模块，声明版本号和 POD 文档 |
| Starlet/Server.pm | HTTP/1.1 服务器实现 |
| Plack/Handler/Starlet.pm | Plack 处理器接口，支持 prefork 模式 |

## 使用说明

Starlet 是一个高性能 PSGI/Plack HTTP 服务器，适合作为反向代理后端的应用服务器。

### 环境配置

```bash
# 设置 PERL5LIB（如果依赖安装在用户目录）
export PERL5LIB=/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.0
export TMPDIR=/storage/Users/currentUser/tmp  # 避免使用只读 /tmp
```

### 启动方式

```bash
# 使用 plackup 启动
plackup -s Starlet --port=8080 your-app.psgi

# 直接 Perl 启动
perl -MPlack::Handler::Starlet -e '
  my $app = sub { [200, ["Content-Type"=>"text/plain"], ["hello"]] };
  Plack::Handler::Starlet->new(host=>"127.0.0.1", port=>8080, max_workers=>0)->run($app);
'
```

### 主要选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| --max-workers | 10 | 工作进程数（0=单进程） |
| --timeout | 300 | 请求超时（秒） |
| --keepalive-timeout | 2 | 持久连接超时（秒） |
| --max-keepalive-reqs | 1 | 每连接最大请求数 |
| --max-reqs-per-child | 100 | 每进程最大请求数 |

### 平台注意事项

1. **XS模块替代**: Proc::Wait3 和 Clone 的 XS 版本 (.so) 无法从用户目录加载，需使用纯 Perl 替代
2. **sudo不可用**: OpenHarmony 上 sudo 无法提权，依赖模块需安装到用户本地目录
3. **/tmp 只读**: 使用 `$TMPDIR` 替代 `/tmp`
4. **HTTP验证通过**: GET/POST/路由全部正常，响应头包含 Date/Server/Content-Type/Content-Length

---
*OpenHarmony 编译归档 · 2026-07-06*
