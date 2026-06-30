# perl-ppix-quotelike 0.023 适配笔记

## 编译环境
- 构建系统: perl-eumm (ExtUtils::MakeMaker, Makefile.PL)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (纯 Perl 模块，实际未使用 C 编译器)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. 初始化构建环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-ppix-quotelike 0.023
   source .build-context-perl-ppix-quotelike-0.023
   ```

2. 设置环境变量（参考 perl-dbd-pg 编译经验）：
   ```bash
   export PERL5LIB=$DEFAULT_PREFIX/lib/site_perl/5.42.0:$DEFAULT_PREFIX/lib/perl5/site_perl:$DEFAULT_PREFIX/lib/perl5:$PERL5LIB
   export PERL_PARAMS_UTIL_PP=1
   ```

3. 编译安装：
   ```bash
   cd $BUILD_SRC_DIR
   perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site
   make -j1
   make install DESTDIR=$TEST_PREFIX
   ```

4. 测试：
   ```bash
   make test
   ```

5. 生成 Conan 配方并验证：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py conan-init perl-ppix-quotelike 0.023
   python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-ppix-quotelike 0.023
   ```

6. 收尾：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py finish perl-ppix-quotelike 0.023 published
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Readonly 模块缺失 | Module::Build::Tiny 不可用，无法通过 cpan 安装 | 手动从 CPAN 下载 Readonly 模块 tarball，解压后直接拷贝 .pm 文件到 site_perl 目录 |
| 2 | Params::Util XS .so 无法加载 | 鸿蒙 HMDFS 上 SELinux 限制 .so dlopen | 设置 `PERL_PARAMS_UTIL_PP=1` 环境变量使用纯 Perl 实现 |
| 3 | PERL5LIB 路径不完整 | PPI 模块安装路径未被默认 @INC 包含 | 在 PERL5LIB 中添加 `$DEFAULT_PREFIX/lib/site_perl/5.42.0` |
| 4 | SSL 证书验证失败 | 鸿蒙平台 CA 证书配置问题 | 使用 `curl -k` 下载 tarball（参考 perl-dbd-pg 经验） |

## 源码修改

无补丁。纯 Perl 模块，源码无需修改即可在鸿蒙平台编译运行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| PPI | 1.284 | Perl 源码解析基础库（已编译安装） |
| Readonly | 2.05 | 只读变量支持（手动安装） |
| Params::Util | 1.10 | 参数工具（纯 Perl 模式运行） |
| Perl | 5.42.0 | 系统自带 |

## 验证结果

```bash
# 原始测试套件
$ make test
t/basic.t ............................ ok
t/dump.t ............................. ok
t/locations.t ........................ ok
t/normalize_interpolation_for_ppi.t .. ok
t/parse.t ............................ ok
t/unit-adhoc.t ....................... ok
t/variables.t ........................ ok
t/version.t .......................... ok
All tests successful.
Files=8, Tests=743, 2 wallclock secs
Result: PASS

# 功能验证
$ perl -MPPIx::QuoteLike -e 'print "OK\n"; print "Version: ", PPIx::QuoteLike->VERSION, "\n";'
OK
Version: 0.023

# Conan 验证 (G0-G4 + L2/L4/L5 全部 PASS)
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-ppix-quotelike 0.023
G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS | L2: PASS | L4: PASS | L5: PASS
```

## 注意事项

1. 纯 Perl 模块，无需静态链接配置（R26 豁免）
2. test_package 的 PERL5LIB 需同时包含 Conan 包路径和系统 Perl 依赖路径
3. PPI 1.284 必须先于 PPIx::QuoteLike 编译安装
4. `PERL_PARAMS_UTIL_PP=1` 必须在测试和运行时设置
---

**编译结束**: 2026-06-26 14:42
**最终状态**: built
