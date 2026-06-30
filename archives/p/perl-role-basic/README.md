# perl-role-basic

Perl 轻量级角色（Role）实现模块（Role::Basic），Moose::Role 的替代方案。

## 软件信息

- **官网**: https://metacpan.org/dist/Role-Basic
- **源码**: https://cpan.metacpan.org/authors/id/O/OV/OVID/Role-Basic-0.16.tar.gz
- **许可证**: perl_5
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.16 | published | 2026-06-29 | 纯 Perl 模块，无需特殊适配。304 测试全通过 |

## 运行依赖

- perl 5.42.0

## 编译依赖

无额外依赖（纯 Perl 模块）

## 使用说明

Role::Basic 提供轻量级的角色（Role）组合功能，支持 `with`、`requires`、方法排除（`-excludes`）和方法别名（`-alias`）。不含 `has` 属性定义和方法修饰器（before/after/around），设计目标是安全与简洁。

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-role-basic/0.16@ohpcd/stable
```

模块安装到 `lib/perl5/Role/Basic.pm`，通过 `PERL5LIB` 环境变量自动加载。

### 示例

```perl
# 定义角色
package Role::Printable;
use Role::Basic;
sub to_string { return "I am printable" }

# 定义带 requires 的角色
package Role::Named;
use Role::Basic;
requires 'name';
sub greeting { return "Hello, " . shift->name }

# 消费角色
package My::Class;
use Role::Basic 'with';
with qw(Role::Printable Role::Named);
sub name { return "World" }

# 使用
my $obj = bless {}, 'My::Class';
print $obj->to_string();  # I am printable
print $obj->greeting();   # Hello, World
```

### 注意事项

- 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名
- `with` 只能对同一个包调用一次，多角色需在单次调用中传入
- 不支持 `has` 属性定义（那是 Moose 的功能）
- 不支持方法修饰器（before/after/around）
- 类方法会静默覆盖 Role 提供的同名方法
- 无平台特殊限制，可在鸿蒙系统正常使用

---
*OpenHarmony 编译归档 · 2026-06-29*
