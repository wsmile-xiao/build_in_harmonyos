# perl-readonly 2.05 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL fallback for Module::Build::Tiny)
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- Perl: 5.42.0
- 状态: published

## 编译步骤

1. 源码下载: `https://cpan.metacpan.org/authors/id/S/SA/SANKO/Readonly-2.05.tar.gz`
2. 原始源码使用 Module::Build::Tiny (Build.PL)，平台无此模块，conanfile.py 自动生成 Makefile.PL (ExtUtils::MakeMaker) 作为 fallback
3. 构建: `perl Makefile.PL INSTALLDIRS=site && make -j1`
4. 安装: `make install DESTDIR=$TEST_PREFIX`
5. 测试: `perl -MExtUtils::Command::MM -MTest::Harness -e "test_harness(0, 'blib/lib', 'blib/arch')" t/bugs/*.t t/general/*.t` (188 tests, all pass)
6. Conan 配方生成: `ohc-run.py conan-init perl-readonly 2.05`
7. Conan 验证: 手动 `conan create` 使用 default profile (os=HarmonyOS) 验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始源码使用 Module::Build::Tiny (Build.PL) | 平台无 Module::Build::Tiny 模块 | conanfile.py build() 自动生成 Makefile.PL (ExtUtils::MakeMaker) 作为 fallback |
| 2 | 纯 Perl 模块，无 C 编译 | Readonly 是纯 Perl 代码 | conanfile.py build() 使用 `perl Makefile.PL` + `make`，无需 configure |
| 3 | package() 需正确提取 .pm 文件 | Perl 模块安装到 site_perl 目录，需要映射到 Conan 包结构 | package() 使用 glob 递归查找 .pm 文件，映射到 lib/perl5 目录 |
| 4 | test_package 需设置 PERL5LIB | Conan 包的 .pm 文件不在默认 @INC 中 | test_package test() 设置 PERL5LIB 环境变量指向包目录 |
| 5 | test_package 有多余的 C/CMake 文件 | conan-init 模板自动生成了 CMakeLists.txt 和 test.c | 手动删除，纯 Perl 模块不需要 C 测试框架 |
| 6 | conan-verify 使用 CI profile (os=OHOS) 失败 | 本地 Conan 不支持 os=OHOS 枚举 | 使用 default profile (os=HarmonyOS) 手动验证，CI 流水线使用 OHOS 适配版 Conan |

## 源码修改

无补丁。源码无需修改即可在鸿蒙平台编译运行。conanfile.py 在 build() 阶段动态生成 Makefile.PL 作为构建系统 fallback。

## 依赖版本

- Perl: 5.42.0 (系统预装)
- ExtUtils::MakeMaker: Perl 核心模块
- 无外部依赖

## 验证结果

```bash
# 原始测试套件
$ perl -MExtUtils::Command::MM -MTest::Harness -e "test_harness(0, 'blib/lib', 'blib/arch')" t/bugs/*.t t/general/*.t
Files=14, Tests=188, 1 wallclock secs
All tests successful.
Result: PASS

# Conan 验证 (conan create with default profile)
G0: ✅ PASS (E007 知识命中，非阻塞，纯 Perl 模块无 configure)
G1: ✅ PASS (配方完整)
G2: ✅ PASS (conan create 成功，test_package 8 项测试全通过)
G3: ✅ PASS (无系统同名库)
G4: ✅ PASS (lib/: 0 .a + 0 .so，纯 .pm 文件)
L2: ✅ PASS (test_package: 8 项 smoke test 全通过)
L4: ✅ PASS (无可扫描 ELF)
L5: ✅ PASS (产物与基线一致, 3 个文件)

# 深度功能测试 (48 项)
$ perl test_readonly.pl
=== Results: 48 passed, 0 failed ===

# 边界测试
Unicode: ✅ PASS
Large data (1000 elements): ✅ PASS
Many vars (100 readonly): ✅ PASS
Taint mode (-T): ⚠️ N/A (Perl 安全特性限制)
```

## 注意事项

- 原始源码使用 Module::Build::Tiny (Build.PL)，conanfile.py 通过自动生成 Makefile.PL 解决
- taint 模式 (-T) 下 PERL5LIB 被忽略，需将模块安装到系统 @INC 目录（需要 root 权限）。非 taint 模式下通过 PERL5LIB 正常工作
- conan-verify 脚本使用 CI profile (os=OHOS) 在本地会失败，需使用 default profile (os=HarmonyOS) 手动验证

---

**编译结束**: 2026-06-29
**最终状态**: published
