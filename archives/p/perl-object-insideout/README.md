# perl-object-insideout

Comprehensive inside-out object support module for Perl.

## 简介

Object::InsideOut 是一个全面的 Perl 面向对象编程模块，提供 inside-out 对象模型支持。它提供了字段定义、类型约束、继承、多重继承、方法属性、对象序列化、克隆、析构等完整的 OOP 功能。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 4.05-r7 | published | 2026-07-01 | 鸿蒙平台适配，Conan 配方验证通过 |

## 使用方法

### Conan 安装

```bash
conan install --requires=perl-object-insideout/4.05-r7
```

### Perl 代码示例

```perl
package My::Class; {
    use Object::InsideOut;

    my @data
        :Field
        :Type(scalar)
        :Accessor(data)
        :Arg(Name => 'data', Default => 'default');
}

package main;
my $obj = My::Class->new(data => 'hello');
print $obj->data();  # 输出: hello
```

## 平台兼容性

| 平台 | 状态 | 说明 |
|------|------|------|
| OpenHarmony (aarch64) | ✅ 完全可用 | 纯 Perl 模块，无平台限制 |
| Linux (aarch64) | ✅ 兼容 | 标准 Perl 环境 |

## 依赖

- Perl 5.x (系统自带)
- ExtUtils::MakeMaker (Perl 核心模块)
- 可选: Want, Math::Random::MT::Auto (未安装不影响核心功能)

## 许可证

Artistic License 1.0 (Perl)
