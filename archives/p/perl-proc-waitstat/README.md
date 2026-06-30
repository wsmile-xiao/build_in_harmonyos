# perl-proc-waitstat

Perl module `Proc::WaitStat` — Interpret and act on wait() status values.

## 描述

Proc::WaitStat 提供用于解释和操作 `wait()` 状态值的函数。支持将状态值转换为可读字符串（如 "0"、"42"、"killed (SIGHUP)"）、转换为 shell 风格退出码（信号死亡时返回 128+信号号）、以及在非零退出时自动 die。

### 导出函数

| 函数 | 原型 | 说明 |
|------|------|------|
| `waitstat($?)` | `$` | 返回 wait 状态的字符串描述 |
| `waitstat_reuse($?)` | `$` | 转换为 shell 风格退出码 |
| `waitstat_die($?, $prog)` | `$$` | 非零状态时 die |
| `close_die(*FH, $name)` | `*$` | 关闭文件句柄，失败时 die |

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.00 | published | 2026-06-26 |

## 构建系统

ExtUtils::MakeMaker (perl-eumm)

## 依赖

- Perl >= 5.003_98
- IPC::Signal (sig_name 函数)
- POSIX (:sys_wait_h)

## 许可证

perl_5 (Perl 5 programming language license)
