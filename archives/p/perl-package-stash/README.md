# perl-package-stash

Routines for manipulating stashes (Package::Stash CPAN module).

## 软件信息

- **官网**: https://metacpan.org/dist/Package-Stash
- **源码**: https://github.com/moose/Package-Stash
- **许可证**: Perl (Artistic-1.0-Perl OR GPL-1.0-or-later)
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.40-r1 | built | 2026-07-02 | PP 实现完全可用，268 项 CPAN 测试通过 |

## 运行依赖

- perl (5.42.0+)
- perl-module-implementation (>= 0.06)
- perl-dist-checkconflicts (>= 0.02)

## 编译依赖

- perl (5.42.0+)
- perl-module-implementation (>= 0.06)
- perl-dist-checkconflicts (>= 0.02)

## 使用说明

Package::Stash 提供了对 Perl 符号表 (stash) 的操作接口，用于添加、获取、移除和列出包变量。

### 安装

```bash
# 通过 Conan 安装
conan install --requires=perl-package-stash/0.40-r1
```

### 示例

```perl
use Package::Stash;

my $stash = Package::Stash->new('Foo');
$stash->add_symbol('%foo', {bar => 1});
# $Foo::foo{bar} == 1

$stash->has_symbol('$foo');  # false
my $namespace = $stash->namespace;
```

### 注意事项

1. **PP 实现**: 在 OpenHarmony 平台上使用 PP (Pure Perl) 实现，因 SELinux 限制 XS .so 无法从用户目录加载
2. **功能完整**: PP 实现提供 100% 功能等价，全部 268 项 CPAN 测试通过
3. **XS 可选**: 如需 XS 性能，可将 XS.so 安装到 `/data/service/hnp` 系统目录
4. **构建系统**: 使用 `perl Makefile.PL --pureperl-only` 构建，INSTALL_BASE 需在 Makefile.PL 阶段设置

---
*OpenHarmony 编译归档 · 2026-07-02*
