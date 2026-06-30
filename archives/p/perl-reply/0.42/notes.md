# perl-reply 0.42 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 CPAN 下载 Reply-0.42.tar.gz 源码
2. 运行 `perl Makefile.PL INSTALLDIRS=site` 配置
3. 运行 `make -j1` 编译
4. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging
5. 下载 15 个纯 Perl 依赖模块并打包到 lib/perl5
6. 修补 Mixin::Linewise::Readers 使 PerlIO::utf8_strict 可选
7. 修补 reply 脚本自定位 lib 目录 + 强制纯 Perl 模式
8. 清理原始 Perl 安装树，仅保留 bin/ 和 lib/perl5

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | reply --version 失败：Can't locate Module/Runtime.pm | 纯Perl依赖模块未安装在系统中 | 下载并bundle 15个纯Perl依赖到 lib/perl5 |
| 2 | Can't locate PerlIO/utf8_strict.pm | PerlIO::utf8_strict 是XS模块，.so在OHOS上无法加载(SELinux) | 修补 Mixin::Linewise::Readers 使其可选，回退到 :utf8 |
| 3 | Can't locate loadable object for Params::Util | Params::Util 有XS后端，.so无法加载 | 设置 PERL_PARAMS_UTIL_PP=1 强制纯Perl模式 |
| 4 | Package::Stash 尝试加载 XS 后端 | Package::Stash::XS 的 .so 无法加载 | 设置 PACKAGE_STASH_IMPLEMENTATION=PP |
| 5 | L2 smoke test 失败：reply 二进制无法运行 | 脚本无法找到 lib/perl5 目录(PERL5LIB 未设置) | 修补 reply 脚本 BEGIN 块自定位 lib 目录 |
| 6 | SSL 证书验证失败 (urllib) | Conan 构建环境缺少 CA 证书 | 改用 curl 下载依赖 |
| 7 | REPL模式报错: Can't locate Devel/LexAlias.pm | Eval::Closure 使用 Devel::LexAlias (XS) 实现词法变量别名 | 修补 Eval::Closure 使 Devel::LexAlias 可选 (eval require) |
| 8 | REPL模式报错: Can't locate PadWalker.pm | 默认配置含 [LexicalPersistence] 插件，依赖 PadWalker (XS) | 从 Reply::App 默认配置中移除 [LexicalPersistence] |
| 9 | REPL交互模式挂起(管道输入时) | 默认配置含 [ReadLine] 插件，Term::ReadLine 在OHOS管道场景下阻塞 | 从默认配置移除 [ReadLine] 和 [FancyPrompt] |

## 源码修改

### 内联修补（conanfile.py package() 方法中执行）

1. **Mixin/Linewise/Readers.pm**: 将 `use PerlIO::utf8_strict;` 改为可选加载，回退到 `:utf8`
2. **Eval/Closure.pm**: 将 `require Devel::LexAlias;` 包裹在 `eval { ... }` 中，使 Devel::LexAlias (XS) 可选
3. **Reply/App.pm**: 从默认配置 (`__DATA__` 段) 移除三个依赖 XS 的插件:
   - `[LexicalPersistence]` — 依赖 PadWalker (XS)
   - `[ReadLine]` — Term::ReadLine 在 OHOS 管道场景下阻塞
   - `[FancyPrompt]` — 依赖 ReadLine 获取终端宽度
4. **bin/reply**: 添加 BEGIN 块：
   - 自定位 `../lib/perl5` 目录（使用 File::Basename + File::Spec）
   - 设置 `PERL_PARAMS_UTIL_PP=1` 和 `PACKAGE_STASH_IMPLEMENTATION=PP`

## 依赖版本

### 系统核心模块（已存在）
- Perl 5.42.0 (/data/service/hnp/perl.org/perl_5.42.0/bin/perl)
- Scalar::Util, Getopt::Long, Data::Dumper, File::Spec, Term::ANSIColor, Time::HiRes

### Bundled 纯 Perl 依赖
- Module::Runtime 0.016
- Try::Tiny 0.32
- Config::INI 0.025 + Config::INI::Reader::Ordered 0.022
- File::HomeDir 1.006 + File::Which 1.27
- Eval::Closure 0.14
- Package::Stash 0.40 (PP 模式)
- Dist::CheckConflicts 0.11
- Module::Implementation 0.09
- Mixin::Linewise 0.111 (patched)
- Sub::Exporter 0.991 + Sub::Install 0.929
- Params::Util 1.102 (PP 模式)
- Data::OptList 0.114

### XS 模块（无法在 OHOS 加载，功能受限）
- PadWalker（LexicalPersistence 插件依赖）
- Devel::LexAlias（LexicalPersistence 插件依赖）
- PerlIO::utf8_strict（已通过修补回退到 :utf8）

## 验证结果

### 基本功能
```bash
$ reply --version
Reply version 0.42

$ reply --help
    reply [-lb] [-I dir] [-M mod] [--version] [--help] [--cfg file]
```

### REPL 功能测试

| 测试 | 输入 | 输出 | 结果 |
|------|------|------|------|
| 算术 | `1 + 2` | `3` | ✅ |
| 字符串 | `scalar reverse("hello")` | `olleh` | ✅ |
| 全局变量 | `$main::x = 42; $main::x * 2` | `84` | ✅ |
| JSON | `use JSON::PP; encode_json({name=>"OHOS"})` | `{"name":"OHOS"}` | ✅ |
| Data::Dumper | `use Data::Dumper; Dumper({a=>1})` | 正确输出 | ✅ |
| map/grep | `join(",", map {$_*2} grep {$_>1} (1,2,3,4))` | `4,6,8` | ✅ |
| 正则 | `"Hello World" =~ /(\w+) (\w+)/; "$2 $1"` | `World Hello` | ✅ |
| 子程序 | `sub square { $_[0] ** 2 } square(7)` | `49` | ✅ |
| 模块加载 | 9个依赖模块逐一 `require` | 全部成功 | ✅ |

### 已知限制
- 词法变量 (`my $x`) 不跨行持久（LexicalPersistence/PadWalker XS 不可用）
- 全局变量 (`$main::x`) 可跨行持久（使用全限定名）
- 单行多表达式正常工作（分号分隔）

conan-verify 全部通过: G0 ✅ G1 ✅ G2 ✅ G3 ✅ G4 ✅ L2 ✅ L4 ✅ L5 ✅

## 注意事项

- reply 脚本已修补为自定位模式，无需设置 PERL5LIB 即可运行
- XS 模块 (PadWalker, Devel::LexAlias) 无法在 OHOS 加载，已从默认配置移除相关插件
- 默认配置已移除 [LexicalPersistence]、[ReadLine]、[FancyPrompt] 三个插件
- 保留的纯 Perl 插件: Interrupt, DataDumper, Colors, Hints, Packages, ResultCache, Autocomplete::*
- Eval::Closure 已修补为 Devel::LexAlias 可选（eval require 模式）
- 词法变量(my)不跨行持久，全局变量($main::x)可持久，单行多表达式正常
- 参考 perl-dbd-pg 编译经验：XS 模块在 OHOS 上需要特殊处理（.so 加载限制）

---
**编译结束**: 2026-06-29 20:22
**最终状态**: published
