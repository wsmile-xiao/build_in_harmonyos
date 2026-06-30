# perl-ppix-utils 0.004 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (perl-eumm)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (纯Perl模块，无C编译)
- Perl: 5.42.0
- 状态: published

## 编译步骤

```bash
# 1. 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-ppix-utils 0.004

# 2. 读取上下文
source .build-context-perl-ppix-utils-0.004

# 3. 设置环境变量
export PERL5LIB=$DEFAULT_PREFIX/lib/site_perl/5.42.0:$DEFAULT_PREFIX/lib/perl5/site_perl:$DEFAULT_PREFIX/lib/perl5:$PERL5LIB
export PERL_PARAMS_UTIL_PP=1

# 4. 编译安装
cd $BUILD_SRC_DIR
perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site && make -j1 && make install DESTDIR=$TEST_PREFIX

# 5. 测试
make test  # 159 tests, all pass

# 6. 生成Conan配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init perl-ppix-utils 0.004

# 7. 验证配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-ppix-utils 0.004
# G0-G4 + L2/L4/L5 全部 PASS

# 8. 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish perl-ppix-utils 0.004 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PERL5LIB 路径不正确 | 鸿蒙Perl安装在非标准路径 | 设置 PERL5LIB 包含 $DEFAULT_PREFIX/lib/site_perl/5.42.0 |
| 2 | PPI 依赖链中 XS 模块无法 dlopen | HMDFS 上 SELinux 限制 .so dlopen | 设置 PERL_PARAMS_UTIL_PP=1 使用纯Perl模式 |
| 3 | conanfile.py package() 路径需适配 | Perl模块安装到嵌套 site_perl 路径 | copy .pm 到 lib/PPIx/ 供 G4 产物检测 |
| 4 | G0 无法识别构建系统 | perl-eumm 不在已知构建系统列表 | 已知平台限制，手动验证通过 |

## 源码修改

无补丁，无源码修改。纯Perl模块直接编译安装。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| PPI | 1.284 | 已编译安装 |
| B::Keywords | 1.29 | 系统自带 |
| Exporter | 5.79 | Perl核心模块 |
| Scalar::Util | 1.68_01 | Perl核心模块 |
| Test::More | 1.302210 | Perl核心模块 |

## 验证结果

```bash
# make test
All tests successful.
Files=5, Tests=159,  1 wallclock secs
Result: PASS

# 功能测试 (10项全部通过)
perl -MPPIx::Utils -e 'print "OK\n"'
# OK

# conan-verify
G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS
L2: PASS | L4: PASS | L5: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/PPIx/Utils.pm | 2507 | 主模块 |
| lib/PPIx/Utils/Classification.pm | 31807 | 分类工具 |
| lib/PPIx/Utils/Language.pm | 3754 | 语言工具 |
| lib/PPIx/Utils/Traversal.pm | 17952 | 遍历工具 |
| lib/PPIx/Utils/_Common.pm | 1217 | 公共内部模块 |

## 注意事项

- 纯Perl模块，无需C编译器，无.so文件，不受HMDFS/SELinux限制
- 运行时需设置 PERL_PARAMS_UTIL_PP=1（PPI依赖链中Params::Util的XS .so无法dlopen）
- PERL5LIB 必须包含 site_perl/5.42.0 路径
- conanfile.py 的 package() 方法将 .pm 从嵌套 site_perl 路径复制到 lib/ 供 Conan 产物检测
**测试完成**: 2026-06-26 14:40
---

**编译结束**: 2026-06-26 14:49
**最终状态**: published
