# Devel::CheckCompiler

## 简介
Check the compiler's availability. Detects if the system has a working C99 compiler. Useful for Perl modules that require C compilation during their build process.

## OHOS 适配
- **纯 Perl 模块**: 无 XS 代码，无需编译 C 代码到原生库
- **C99 检测受限**: `-fstack-protector-strong` 标志与 OHOS ld.lld 不兼容
- **安装方式**: `perl Build.PL && ./Build && ./Build install`
- **依赖**: perl 5.8.1+, ExtUtils::CBuilder, Module::Build

## 功能验证
```bash
perl -MDevel::CheckCompiler -e 'print "Devel::CheckCompiler loaded\n"'
```

## OHOS 限制
- C99 检测返回 NO（链接器标志兼容性问题）
- 模块仍可用于基本编译器检测（编译测试）
- 其他 Perl 模块可以使用此模块作为构建依赖

## 测试结果（2026-06-11）
- ✅ 核心功能通过：模块加载、版本验证、函数导出
- ⚠️ 环境限制：C99 检测失败（ld.lld 不支持 -fstack-protector-strong）
- ✅ 适合发布：参考 ExtUtils::CChecker 发布策略

## 预编译包
- 文件：Devel-CheckCompiler-0.03-ohos-aarch64.tar.gz (8KB)
- 内容：lib/perl5/Devel/CheckCompiler.pm, lib/perl5/Devel/AssertC99.pm
- 类型：纯 Perl 模块

## 参考
- CPAN: https://metacpan.org/pod/Devel::CheckCompiler
- 源码: https://cpan.metacpan.org/authors/id/T/TO/TOKUHIROM/Devel-CheckCompiler-0.03.tar.gz
- 相关模块：ExtUtils::CChecker（相似限制已发布）