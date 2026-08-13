# perl-parallel-forkmanager

Perl parallel processing fork manager — 简单的并行进程管理模块。

## 软件信息

- **官网**: https://metacpan.org/release/Parallel-ForkManager
- **源码**: https://cpan.metacpan.org/modules/by-module/Parallel/Parallel-ForkManager-2.04.tar.gz
- **许可证**: Perl_5 (Artistic License 1.0 或 GPL)
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.04 | published | 2026-07-03 | 纯 Perl 模块，conan-verify + CI 模拟全部通过，34 项功能测试 ALL PASS |

## 运行依赖

- perl 5.42.0+

## 编译依赖

无外部依赖。纯 Perl 模块，仅需 perl 运行时。

## 使用说明

Parallel::ForkManager 提供简单的并行进程管理，支持：
- 并行 fork 子进程
- 限制最大并发进程数
- run_on_start / run_on_finish / run_on_wait 回调
- 子进程数据返回

### 安装

```bash
conan install --requires=perl-parallel-forkmanager/2.04@ohpcd/stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

### 基本用法

```perl
use Parallel::ForkManager;

my $pm = Parallel::ForkManager->new(4);  # 最多 4 个并行进程

$pm->run_on_finish(sub {
    my ($pid, $exit_code, $ident, $signal, $dump, $data) = @_;
    print "Child $ident exited with code $exit_code\n";
});

for my $item (@items) {
    $pm->start($item) and next;
    # 子进程中执行任务
    do_work($item);
    $pm->finish(0, { result => $item });
}
$pm->wait_all_children;
```

### 注意事项

- 纯 Perl 模块，无 XS/C 代码，不受 SELinux HMDFS 限制
- fork() 在鸿蒙 OHOS 平台正常工作
- 与 perl-dbd-pg 等 XS 模块不同，无需安装到系统目录

---
*OpenHarmony 编译归档 · 2026-07-06*
