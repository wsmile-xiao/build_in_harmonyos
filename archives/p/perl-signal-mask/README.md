# perl-signal-mask

Signal::Mask — Signal masks made easy. Pure Perl module providing easy access to signal masks and pending signals.

## 软件信息

- **官网**: https://metacpan.org/dist/Signal-Mask
- **源码**: https://github.com/Leont/signal-mask
- **许可证**: perl_5
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.008-r3 | published | 2026-06-29 | 纯 Perl 模块，无需适配，conan-verify 全部通过 |

## 运行依赖

- perl (v5.42.0)
- perl-ipc-signal (IPC::Signal 模块)

## 编译依赖

- perl
- make

## 使用说明

Signal::Mask 提供对信号掩码（sigprocmask）和待处理信号（sigpending）的简单 Perl 接口。

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-signal-mask/0.008-r3@ohpcd/stable
```

安装后，模块文件位于 `lib/perl5/site_perl/5.42.0/Signal/` 目录下。

### 基本用法

```perl
use Signal::Mask;
use Signal::Pending;

# 阻塞 SIGUSR1
$Signal::Mask{USR1} = 1;

# 发送信号给自己（会被阻塞，进入 pending）
kill SIGUSR1 => $$;

# 检查信号是否 pending
print "USR1 pending" if $Signal::Pending{USR1};

# 解除阻塞（信号将被递送）
delete $Signal::Mask{USR1};
```

### 注意事项

- 纯 Perl 模块，不涉及 C/XS 编译，无需特殊平台适配
- 运行时依赖 IPC::Signal 模块，需确保系统 Perl 的 site_perl 路径在 PERL5LIB 中
- 信号掩码和待处理信号功能在 OpenHarmony 6.0 上行为与标准 Linux 一致

---
*OpenHarmony 编译归档 · 2026-06-29*
