# perl-number-compare

Perl module **Number::Compare** — numeric comparisons with magnitude support.

## 简介

Number::Compare 将简单的比较表达式编译为匿名子程序，支持千字节(k/ki)、兆字节(m/mi)、吉字节(g/gi)数量级后缀。

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.03-r5 | built | 2026-06-29 | OpenHarmony OHOS aarch64 适配，Conan 配方验证通过 |

## 使用方法

```bash
# 通过 Conan 安装
conan install --requires=perl-number-compare/0.03-r5

# Perl 代码中使用
use Number::Compare;
my $comp = Number::Compare->new('>1Ki');
print $comp->test(1025) ? "yes" : "no";  # yes (1025 > 1024)
```

## 支持的比较运算符

| 表达式 | 含义 | 示例 |
|--------|------|------|
| `>N` | 大于 | `>10` |
| `<N` | 小于 | `<10` |
| `>=N` | 大于等于 | `>=10` |
| `<=N` | 小于等于 | `<=10` |
| `N` | 等于（裸数字） | `10` |

## 数量级后缀

| 后缀 | 倍数 | 说明 |
|------|------|------|
| `k` | 1000 | 千 |
| `ki` | 1024 | Kib |
| `m` | 1000000 | 兆 |
| `mi` | 1048576 | Mib |
| `g` | 1000000000 | 吉 |
| `gi` | 1073741824 | Gib |

## OpenHarmony 适配说明

- 纯 Perl 模块，无需 C 编译器
- 不受 SELinux HMDFS 限制（与 XS 模块不同）
- 使用 ExtUtils::MakeMaker 构建系统
- Conan 配方已验证通过（G1-G4 + L2/L4/L5 全部 PASS）
