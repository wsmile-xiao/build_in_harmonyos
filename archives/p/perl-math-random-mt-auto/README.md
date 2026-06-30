# perl-math-random-mt-auto

Mersenne Twister 随机数生成器的 Perl XS 实现，提供高质量的伪随机数。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 6.23-r10 | published | 2026-06-17 |

## 功能

- **irand()** — 32 位无符号整数随机数
- **rand()** — [0,1) 浮点随机数
- **gaussian()** — 高斯(正态)分布随机数
- **exponential()** — 指数分布随机数
- **erlang()** — 埃尔朗分布随机数
- **seed_prng()** — 设置随机种子
- **set_state()** — 设置 PRNG 内部状态
- **free_prng()** — 释放 PRNG

## 依赖

- Perl >= 5.006
- Object::InsideOut >= 3.88
- Exception::Class
- Scalar::Util >= 1.23

## 平台说明

- **架构**: aarch64-unknown-linux-ohos
- **构建系统**: Perl Makefile (ExtUtils::MakeMaker)
- **编译器**: clang 18.1.8

### SELinux 注意事项

XS 模块 (Auto.so) 在 HMDFS 上无法通过 dlopen 加载（SELinux 限制）。
需要安装到 `/data/service/hnp/` 系统目录。已提供 HNP 安装包。
