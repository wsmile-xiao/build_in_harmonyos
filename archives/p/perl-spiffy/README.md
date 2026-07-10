# perl-spiffy

Spiffy Perl Interface Framework For You — pure-Perl module providing mixin, field, const, export, and super() functionality.

## 软件信息

- **官网**: https://metacpan.org/dist/Spiffy
- **源码**: https://github.com/ingydotnet/spiffy-pm
- **许可证**: Perl (Artistic-1.0 或 GPL-1+)
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 验证日期 | 说明 |
|------|------|---------|---------|------|
| 0.46 | built | 2026-07-01 | 2026-07-02 | 纯 Perl 模块，conan-verify 全门禁通过，上游 198 测试全部通过 |

## 运行依赖

- perl (5.42.0)

## 编译依赖

- perl (5.42.0)

## 使用说明

Spiffy 是一个 Perl 面向对象编程框架，提供以下核心功能：

- **mixin**: 将一个类的方法混入另一个类（使用 `use mixin 'Class'` 语法）
- **field**: 声明对象属性（带默认值和访问器）
- **const**: 声明类常量
- **export**: 自动导出函数到调用方
- **super()**: 调用父类同名方法（使用 `use base 'Class'` 语法）

### 安装

Conan 安装：
```bash
conan install --requires=perl-spiffy/0.46@ohpcd/stable
```

### 示例

```perl
use Spiffy;

package My::Class;
use Spiffy -base;
field name => 'default';
const VERSION => '1.0';

package My::Child;
use base 'My::Class';
sub greet { return super() . " from child" }

package main;
my $obj = My::Child->new;
print $obj->name;       # default
print $obj->greet;      # parent from child
```

### 注意事项

- Spiffy 是纯 Perl 模块，无需 C 编译，在鸿蒙平台上可直接使用
- 与 XS 模块（如 perl-dbd-pg）不同，不受 SELinux HMDFS 动态库加载限制
- `use Spiffy -base` 会自动导出 `field`、`const`、`stub`、`super` 等函数
- 测试中 inline package 继承需用 `use base 'Class'`，混入需用 `use mixin 'Class'`

## 测试结果

- **Conan 配方验证**: 全部门禁通过 (G0-G4, L2/L4/L5)
- **Conan L1 测试**: 6/6 通过 (模块加载、field、const、mixin、super、export)
- **上游测试套件**: 32 文件 198 用例全部通过
- **上库自检**: 6/6 PASS

---
*OpenHarmony 编译归档 · 2026-07-02*
