# perl-role-tiny

Perl 轻量级角色（Role）实现模块（Role::Tiny），Moose::Role 的微型替代方案。

## 软件信息

- **官网**: https://metacpan.org/dist/Role-Tiny
- **源码**: https://cpan.metacpan.org/authors/id/H/HA/HAARG/Role-Tiny-2.002004.tar.gz
- **许可证**: perl_5
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.002004 | published | 2026-06-29 | 纯 Perl 模块，无需特殊适配。177 测试全通过 |

## 运行依赖

- perl 5.42.0

## 编译依赖

无额外依赖（纯 Perl 模块）

## 可选运行时依赖

- Class::Method::Modifiers（用于 before/after/around 方法修饰符）

## 使用说明

Role::Tiny 提供轻量级的角色（Role）组合功能，支持 `with`、`requires`、`is_role`、`apply_roles_to_object` 等。可选支持 `before`/`after`/`around` 方法修饰符（需安装 Class::Method::Modifiers）。

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-role-tiny/2.002004
```

模块安装到 `lib/perl5/Role/Tiny.pm` 和 `lib/perl5/Role/Tiny/With.pm`，通过 `PERL5LIB` 环境变量自动加载。

### 示例

```perl
# 定义角色
package Role::Printable;
use Role::Tiny;
sub to_string { return "I am printable" }

# 定义带 requires 的角色
package Role::Named;
use Role::Tiny;
requires 'name';
sub greeting { return "Hello, " . shift->name }

# 消费角色
package My::Class;
use Role::Tiny::With;
with qw(Role::Printable Role::Named);
sub name { return "World" }

# 使用
my $obj = bless {}, 'My::Class';
print $obj->to_string();  # I am printable
print $obj->greeting();   # Hello, World

# 检查角色
print Role::Tiny->is_role("Role::Printable") ? "yes" : "no";  # yes
print $obj->DOES("Role::Printable") ? "yes" : "no";           # yes

# 运行时应用角色
my $late = bless {}, 'SomeClass';
Role::Tiny->apply_roles_to_object($late, "Role::Printable");
print $late->to_string();  # I am printable
```

### 注意事项

- 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名
- `with` 在 Role::Tiny::With 中导入，用于消费角色
- `before`/`after`/`around` 方法修饰符需要安装 Class::Method::Modifiers
- 无 `has` 属性定义（那是 Moose/Moo 的功能）
- 无平台特殊限制，可在鸿蒙系统正常使用

---
*OpenHarmony 编译归档 · 2026-06-29*
