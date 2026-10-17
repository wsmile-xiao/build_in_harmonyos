# perl-package-variant

Package::Variant - Parameterizable packages for Perl.

## 软件信息

- **官网**: https://metacpan.org/dist/Package-Variant
- **源码**: https://git.shadowcat.co.uk/p5sagit/Package-Variant.git
- **许可证**: Perl_5
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.003002-r4 | built | 2026-07-02 | 纯 Perl 模块，编译通过，功能测试全部通过 |

## 运行依赖

- perl (>= 5.006)
- strictures (>= 2.000000)
- Import::Into (>= 1.000000)
- Module::Runtime (>= 0.013)
- Carp (Perl 核心模块)

## 编译依赖

- perl (ExtUtils::MakeMaker 构建系统)
- Test::Fatal (仅测试需要)
- Moo / Moo::Role (仅测试需要)

## 使用说明

Package::Variant 允许在运行时构建可参数化的 Perl 包（variant packages）。用户声明一个 "variable package" 模板，然后通过传递参数生成不同的变体包。

### 基本用法

```perl
# 声明 variable package
package My::VariableRole;
use Package::Variant
    importing => ['Moo::Role'],
    subs => [ qw(has around before after with) ];

sub make_variant {
    my ($class, $target, %args) = @_;
    has $args{name} => (is => 'lazy');
    install "_build_$args{name}" => sub { $args{class}->new };
}

# 使用 variable package 生成变体
package My::Class;
use Moo;
use My::VariableRole;
with VariableRole(name => 'attr', class => 'Some::Class');
```

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-package-variant/1.003002-r4@ohpcd/stable
```

安装后，`PERL5LIB` 环境变量会自动包含模块路径。

### 注意事项

- 这是纯 Perl 模块，不包含 XS/C 代码，无需 ELF 签名
- 不受 SELinux HMDFS 限制（无动态库加载）
- 所有依赖模块已在鸿蒙平台可用
- 使用 `INSTALL_BASE` 方式安装（避免 PREFIX+DESTDIR 路径嵌套）

---
*OpenHarmony 编译归档 · 2026-07-03*
