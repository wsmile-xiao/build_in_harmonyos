# perl-sql-statement 1.414-r1 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++ (未实际使用，纯 Perl 模块)
- 状态: built

## 编译步骤

1. 从 CPAN 下载 SQL-Statement-1.414.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-sql-statement 1.414-r1
3. 运行 `perl Makefile PL` 生成 Makefile
4. 运行 `make -j1` 编译（纯 Perl 模块，仅处理 .pm 文件）
5. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
6. 生成 Conan 配方：ohc-run.py conan-init perl-sql-statement 1.414-r1
7. 验证 Conan 配方：ohc-run.py conan-verify perl-sql-statement 1.414-r1

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py 中 cpp_info.libs 声明了不存在的库 | 纯 Perl 模块无编译库，自动生成时误添加 | 移除 cpp_info.libs 声明，设为空列表 |
| 2 | test_package 仅检查文件存在，未验证功能 | 初始测试过于简单 | 增加 perl -c 语法检查和文件完整性验证 |
| 3 | 运行时依赖 Params::Util 的 XS 组件(.so)无法在 HMDFS 加载 | 鸿蒙 SELinux HMDFS 限制用户目录 .so 加载 | 设置 PERL_PARAMS_UTIL_PP=1 使用纯 Perl 模式 |
| 4 | manifest.yaml 中 build system 标为 autotools | 模板默认值 | 修正为 custom/perl (Makefile.PL) |

## 与 perl-dbd-pg 编译经验对比

| 维度 | perl-dbd-pg (XS 模块) | perl-sql-statement (纯 Perl) |
|------|----------------------|-------------------------------|
| C 编译 | 需要 (Pg.xs → Pg.c → Pg.so) | 不需要 |
| CRT 文件 | 缺失，需 -nostartfiles -nodefaultlibs -lc | 不涉及 |
| 链接参数 | 需要特殊 dynamic_lib 配置 | 不需要 |
| 补丁 | 2个 (Makefile.patch, Makefile.PL.patch) | 无需补丁 |
| HMDFS 限制 | 影响 .so 加载，需安装到系统目录 | 仅影响运行时依赖的 XS 组件 |
| conanfile libs | 声明 Pg.so | 不声明（无编译库） |

## 依赖版本

### 编译依赖
- perl 5.42.0 (系统安装于 /data/service/hnp/perl.org/perl_5.42.0/)

### 运行时依赖（不在 Conan 依赖链中，需系统预装）
- Params::Util 1.102 (XS 模块，HMDFS 上需 PP 模式)
- Clone 0.47
- Module::Runtime 0.016
- Scalar::Util, List::Util, Carp, Errno (Perl 核心模块)

## 验证结果

### Conan 验证 (conan-verify)
- G0 (预构建评估): PASS
- G1 (配方完整性): PASS
- G2 (conan create): PASS
- G3 (系统同名库隔离): PASS
- G4 (产物完整性): PASS
- L2/L4/L5: PASS (跳过，纯 Perl 模块无二进制)

### 功能测试
- 模块加载: PASS (需 PERL_PARAMS_UTIL_PP=1)
- 上游测试套件: 17 个测试文件全部通过
  - 00error.t: 7/7
  - 01prepare.t: 282/282
  - 02execute.t: 70/70
  - 03import.t: 11 (部分 skip)
  - 04idents.t: 37/37
  - 05simple.t: 160/160
  - 06virtual.t: 610/610
  - 08join.t: 321/321
  - 09ops.t: 18/18
  - 10limit.t: 2/2
  - 12eval.t: 13/13
  - 14parse.t: 4/4
  - 15parse.t: 1/1
  - 16parse.t: 7/7
  - 17quoting.t: 44/44
  - 23dialects.t: 2/2
  - 99backtick.t: 33/33

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| SQL/Statement.pm | 80966 bytes | 主模块 |
| SQL/Parser.pm | 103315 bytes | SQL 解析器 |
| SQL/Eval.pm | 16640 bytes | 表达式求值 |
| SQL/Dialects/*.pm | 4 files | SQL 方言支持 |
| SQL/Statement/*.pm | 9 files | 子模块 |

## 注意事项

- 纯 Perl 模块编译无需 C 编译器，但仍需 Perl 环境
- 运行时需要 Params::Util，其 XS 组件在 HMDFS 上需 PP 模式
- conanfile.py 通过 runenv_info 自动设置 PERL_PARAMS_UTIL_PP=1
- test_package 使用 perl -c 语法检查替代完整加载测试（隔离环境无运行时依赖）

---

**编译结束**: 2026-07-03 15:35
**最终状态**: built (编译成功，功能测试通过)
