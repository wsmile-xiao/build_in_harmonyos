# perl-regexp-tr (Regexp::Tr)

Run-time-compiled tr/// objects for Perl.

## 描述

Regexp::Tr 解决 Perl 中 tr/// 必须在编译时已知的问题。通过 eval 将 tr/// 编译一次并存储为对象，允许在循环等场景中高效重复使用。

## API

| 方法 | 说明 |
|------|------|
| `new($from, $to, [$mods])` | 创建 tr/// 对象，支持缓存复用 |
| `bind(\$scalar)` | 对标量引用执行 tr///，返回替换计数 |
| `trans($scalar)` | 对标量执行 tr///，返回结果字符串 |
| `flush()` | 清除内部缓存 |

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.05 | ✅ published | 2026-06-29 |

## 来源

- CPAN: https://metacpan.org/dist/Regexp-Tr
- 作者: Robert Fischer (chia@cpan.org)
- 许可证: Perl (Artistic License 1.0 / GPL dual)
