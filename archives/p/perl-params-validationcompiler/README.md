# perl-params-validationcompiler

Build an optimized subroutine parameter validator once, use it forever.

## 软件信息

- **官网**: https://metacpan.org/dist/Params-ValidationCompiler
- **源码**: https://github.com/DROLSKY/Params-ValidationCompiler
- **许可证**: Artistic-2.0
- **分类**: perl-library

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.31 | built | 2026-07-03 | 纯 Perl 模块，编译成功，Conan 验证通过 |

## 运行依赖

- perl (>= 5.42.0)

## 编译依赖

- perl (提供 Makefile.PL 构建系统)

## 使用说明

Params::ValidationCompiler 是一个 Perl 参数验证模块，用于编译一次参数验证器后反复使用。
支持命名参数和位置参数验证，支持可选参数、默认值、slurpy 参数和返回对象模式。

### 安装

模块安装到 `/usr/local/lib/site_perl/5.42.0/Params/` 目录。
作为纯 Perl 模块，无 XS 依赖，无需特殊链接参数。

### 基本用法

```perl
use Params::ValidationCompiler qw(validation_for);

# 命名参数验证
my $validator = validation_for(
    params => {
        name => { optional => 0 },
        age  => { optional => 1, default => 18 },
    }
);

my %args = $validator->(name => "Alice", age => 30);
```

### 注意事项

- 本模块为纯 Perl 实现，无 XS/C 编译代码，不受鸿蒙 CRT 文件缺失问题影响
- 如需使用类型约束（Type::Tiny/Specio），需额外安装对应模块
- `return_object` 选项可返回对象而非哈希，支持方法调用方式访问参数

---
*OpenHarmony 编译归档 · 2026-07-06*
