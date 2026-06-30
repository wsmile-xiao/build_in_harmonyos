# perl-proc-wait3

Perl extension for the `wait3()` system call (XS/C module).

## 描述

Proc::Wait3 提供对 POSIX `wait3()` 系统调用的 Perl 接口，用于回收子进程并获取资源使用统计（rusage）。

支持阻塞和非阻塞模式，返回子进程 PID、退出状态和 16 个 rusage 字段（用户 CPU 时间、系统 CPU 时间、最大 RSS、页面错误数等）。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.05 | published | 2026-06-26 |

## 构建系统

ExtUtils::MakeMaker (perl-eumm)

## 依赖

- Perl >= 5.006
- libc (wait3, getrusage)

## 许可证

perl_5 (Perl 5 programming language license)
