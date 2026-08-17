# perl-parallel-prefork

A simple prefork server framework for Perl.

## 软件信息

- **官网**: https://metacpan.org/dist/Parallel-Prefork
- **源码**: https://cpan.metacpan.org/authors/id/K/KA/KAZUHO/Parallel-Prefork-0.18.tar.gz
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.18 | built | 2026-07-03 | 纯 Perl 模块，编译成功，功能验证通过 |

## 模块类型

纯 Perl 模块（Pure Perl Module），不包含 XS/C 编译代码。

### 安装文件

| 文件 | 说明 |
|------|------|
| Parallel/Prefork.pm | 主模块 — prefork 服务器框架 |
| Parallel/Prefork/SpareWorkers.pm | Spare Workers 管理 |
| Parallel/Prefork/SpareWorkers/Scoreboard.pm | Scoreboard 子模块 |

## 运行依赖

### Perl 模块依赖

| 模块 | 版本要求 | 类型 | OHOS 可用性 |
|------|---------|------|-------------|
| Class::Accessor::Lite | >= 0.04 | 纯 Perl | ✅ 可用 |
| List::MoreUtils | 任意 | 纯 Perl | ✅ 可用 |
| Proc::Wait3 | >= 0.03 | XS 模块 | ⚠️ .so 需安装到系统目录 |
| Scope::Guard | 任意 | 纯 Perl | ✅ 可用 |
| Signal::Mask | 任意 | 纯 Perl | ✅ 可用 |

### 编译依赖

- perl 5.42.0 (系统自带)
- ExtUtils::MakeMaker (perl 核心模块)

## 使用说明

Parallel::Prefork 是一个简单的 prefork 服务器框架，支持优雅关闭和运行时重新配置。

### 安装

```bash
# Conan 安装
conan install --requires=perl-parallel-prefork/0.18@ohpcd/stable
```

安装后设置 PERL5LIB 指向包的 site_perl 目录。

### 注意事项

1. **Proc::Wait3 .so 加载问题**: 运行时依赖 Proc::Wait3 是 XS 模块，其 .so 文件在 HMDFS 上无法加载（SELinux `hmdfs:s0` 上下文限制）。需要管理员将 `Wait3.so` 安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Proc/Wait3/` 目录。

2. **PERL5LIB 路径**: Conan 的 `package_info()` 设置 PERL5LIB 后会覆盖系统默认路径。消费者需手动追加 `~/usr/local/lib/perl5` 到 PERL5LIB。

### 示例代码

```perl
use Parallel::Prefork;

my $pm = Parallel::Prefork->new({
    max_workers  => 10,
    trap_signals => {
        TERM => 'TERM',
        HUP  => 'TERM',
    }
});

while ($pm->signal_received ne 'TERM') {
    $pm->start(sub {
        # worker process logic
        sleep 1;
    });
}

$pm->wait_all_children();
```

---
*OpenHarmony 编译归档 · 2026-07-06*
