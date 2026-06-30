# perl-provide 0.03 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码下载: `https://cpan.metacpan.org/authors/id/B/BE/BELDEN/provide-0.03.tar.gz`
2. 构建: `perl Makefile.PL INSTALLDIRS=site && make -j1`
3. 安装: `make install DESTDIR=$TEST_PREFIX`
4. 测试: `make test` (14 tests, all pass)
5. Conan 配方生成: `ohc-run.py conan-init perl-provide 0.03`
6. Conan 验证: `ohc-run.py conan-verify perl-provide 0.03` (全部门禁通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 纯 Perl 模块，无 C 编译 | provide 是纯 Perl 代码，使用 ExtUtils::MakeMaker 构建 | conanfile.py build() 使用 `perl Makefile.PL` + `make`，无需 configure |
| 2 | package() 需正确提取 .pm 文件 | Perl 模块安装到 site_perl 目录，需要映射到 Conan 包结构 | package() 使用 glob 递归查找 .pm 文件，映射到 lib/perl5 目录 |
| 3 | test_package 需设置 PERL5LIB | Conan 包的 .pm 文件不在默认 @INC 中 | test_package test() 设置 PERL5LIB 环境变量指向包目录 |
| 4 | `use provide` 需要参数 | provide 的 import() 期望 if/ge/else 参数，无参数会 die | test_package 使用 `require` 加载模块，避免调用 import() |

## 源码修改

无补丁。源码无需修改即可在鸿蒙平台编译运行。

## 依赖版本

- Perl: 5.42.0 (系统预装)
- Exporter: Perl 核心模块
- 无外部依赖

## 验证结果

```bash
# 原始测试套件
$ cd t && perl -I../lib -I./lib provide.t
1..14
ok 1 - exporty1 isa Exporter
...
ok 14 - elsif works

# Conan 验证 (conan-verify)
G0: ✅ PASS (E007 知识命中，非阻塞)
G1: ✅ PASS (配方完整)
G2: ✅ PASS (conan create 成功)
G3: ✅ PASS (无系统同名库)
G4: ✅ PASS (lib/: 0 .a + 0 .so)
L2: ✅ PASS (test_package: provide loaded successfully)
L4: ✅ PASS (无可扫描 ELF)
L5: ✅ PASS (产物与基线一致, 3 个文件)

# 全面功能测试
$ perl test_provide.pl
1..42
ok 1 - provide.pm loaded via require
...
ok 42 - provide->can(...)
=== All tests completed ===
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/site_perl/5.42.0/provide.pm | 10375 bytes | 主模块文件 |

## 注意事项

- 纯 Perl 模块，无平台兼容性问题
- `use provide` 必须带参数（if/elsif/else 语法），无参数会 die
- conanfile.py 的 generate() 使用 AutotoolsToolchain 配置静态链接（R26），但实际纯 Perl 模块不产生二进制文件
- package_info() 设置 cpp_info.libs=[] 和 runenv_info PERL5LIB，符合纯 Perl 模块的 Conan 规范

---

**编译结束**: 2026-06-26 18:03
**功能测试**: 2026-06-29
**最终状态**: published
