# perl-string-rewriteprefix 0.009-r1 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-06
- 编译器: clang/clang++
- 状态: built

## 软件简介

String::RewritePrefix 是一个纯 Perl 模块，用于根据已知前缀集合重写字符串。
它可以将如 `qw(Plugin Mixin +Corporate::Thinger)` 重写为 `qw(MyApp::Plugin MyApp::Mixin Corporate::Thinger)`。
支持字符串前缀替换和代码引用（coderef）前缀。

## 编译步骤

1. 从 CPAN 下载 String-RewritePrefix-0.009.tar.gz
2. 解压源码到 build 目录
3. 设置环境变量：
   - `PERL_PARAMS_UTIL_PP=1` — 绕过 Params::Util XS .so 加载限制（SELinux/HMDFS）
   - `PERL5LIB` — 包含 Sub::Exporter 及其依赖链路径
4. 运行 `perl Makefile.PL` 配置
5. 运行 `make -j1` 编译
6. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging
7. 运行上游测试 `perl -I blib/lib t/basic.t` 和 `perl -I blib/lib t/rewrite_sub.t`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Params::Util XS .so 加载失败 | 鸿蒙 SELinux 限制 HMDFS 文件系统上的 .so 动态加载（与 perl-dbd-pg 相同的 HMDFS 限制） | 设置环境变量 `PERL_PARAMS_UTIL_PP=1` 启用 Params::Util 纯 Perl 模式 |
| 2 | Sub::Exporter 依赖链找不到 | 系统 Perl @INC 不包含用户本地 Perl 库路径 | 设置 `PERL5LIB` 包含 `/storage/Users/currentUser/usr/local/perl5/lib/perl5` 等路径 |
| 3 | 系统Perl路径只读 | `/data/service/hnp/` 为只读文件系统 | 使用 `DESTDIR` 安装到 staging，或复制 .pm 到用户本地 Perl lib |
| 4 | test_package 使用 C/CMake 测试纯 Perl 模块 | ohc-run.py 自动生成的 test_package 使用了 C 模板，不适合纯 Perl 模块 | 替换为 Perl 功能测试脚本 test.pl，直接测试 rewrite API |

## 与 perl-dbd-pg 经验对比

| 方面 | perl-dbd-pg (XS 模块) | perl-string-rewriteprefix (纯 Perl 模块) |
|------|----------------------|----------------------------------------|
| 构建系统 | ExtUtils::MakeMaker | ExtUtils::MakeMaker |
| CRT 文件缺失 | 需要 `-nostartfiles -nodefaultlibs -lc` | 不适用（纯 Perl，无 C 编译链接） |
| SELinux .so 限制 | 直接影响 Pg.so 加载 | 间接影响（Params::Util XS .so 无法加载） |
| 解决方案 | Makefile.PL 添加 dynamic_lib 链接参数 | 环境变量 `PERL_PARAMS_UTIL_PP=1` |
| 依赖管理 | pg_config 包装器 | PERL5LIB 路径设置 |

## 源码修改

无源码修改。纯 Perl 模块，无需补丁。

## 依赖版本

### 运行依赖
- Perl 5.42.0 (系统自带)
- Sub::Exporter >= 0.972 (用户本地 Perl lib)
- Params::Util (通过 Sub::Exporter 间接依赖，需 PERL_PARAMS_UTIL_PP=1)

### 编译依赖
- 无 C 编译依赖（纯 Perl 模块）

## 验证结果

### 上游测试
```bash
$ perl -I blib/lib t/basic.t
1..4
ok 1 - rewrote prefices
ok 2 - from synopsis, code okay
ok 3 - rewrote with import
ok 4 - scalar context

$ perl -I blib/lib t/rewrite_sub.t
1..34
ok 1 - rewriter_1
...
ok 34
# 全部 38 个测试通过 (4 + 34)
```

### 功能验证
```bash
$ perl -e 'use String::RewritePrefix; my @r = String::RewritePrefix->rewrite({ "" => "MyApp::", "+" => "" }, qw(Plugin Mixin Addon +Corporate::Thinger)); print join(", ", @r), "\n"'
MyApp::Plugin, MyApp::Mixin, MyApp::Addon, Corporate::Thinger
```

## 注意事项

1. **PERL_PARAMS_UTIL_PP=1 必须设置** — 否则 Sub::Exporter 依赖链中的 Params::Util XS .so 无法加载
2. **PERL5LIB 路径必须正确** — 需包含 Sub::Exporter 及其依赖的安装路径
3. **纯 Perl 模块无需补丁** — 与 perl-dbd-pg (XS 模块) 不同，纯 Perl 模块无需处理 CRT 文件缺失问题
4. **test_package 必须使用 Perl 测试** — 不能用 C/CMake 测试纯 Perl 模块

## 验证报告

详见 `reports/test-report.md` 和 `reports/conan-verify-report.md`。

- 上游测试: 39/39 通过 (basic.t 4 + rewrite_sub.t 34 + 00-report-prereqs.t 1)
- 消费者测试: 6/6 通过 (test_package/test.pl)
- 边缘测试: 6/6 通过
- Conan 验证: 8/8 门禁通过 (G0-G4 + L2/L4/L5)
- 总计: 51/51 测试通过

---

**编译结束**: 2026-07-06
**最终状态**: built
ed
