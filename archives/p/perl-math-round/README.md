# perl-math-round

Perl extension for rounding numbers with various strategies.

## 描述

Math::Round 提供多种数字舍入函数：

- `round` — 标准四舍五入（半值向无穷大方向）
- `nearest` — 舍入到最近的指定倍数
- `round_even` / `round_odd` — 半值向偶数/奇数舍入
- `round_rand` / `nearest_rand` — 半值随机向上或向下
- `nearest_ceil` / `nearest_floor` — 向上/向下舍入到倍数
- `nlowmult` / `nhimult` — 下一个更低/更高倍数

## 模块类型

**纯 Perl 模块** — 无 XS/C 代码，无需 ELF 签名，不受 SELinux 限制。

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 0.08-r1 | 2026-06-17 | published | 首次编译，所有测试通过 |

## 安装方法

```bash
tar xzf perl-math-round-0.08-r1.tar.gz
cd Math-Round-0.08
perl Makefile.PL PREFIX=~/usr/local
make
make test
make install
```

安装后验证：
```bash
perl -MMath::Round -e 'print $Math::Round::VERSION'
```

## 依赖

- Perl >= 5.006（核心模块 POSIX、Exporter、parent）
