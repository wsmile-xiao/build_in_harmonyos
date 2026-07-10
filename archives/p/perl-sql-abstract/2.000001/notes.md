# perl-sql-abstract 2.000001 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-01
- 编译器: clang/clang++（纯 Perl 模块，实际未使用 C 编译器）
- 状态: published

## 编译步骤

1. 从 CPAN 下载 SQL-Abstract-2.000001.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-sql-abstract 2.000001
3. 设置 PERL5LIB 环境变量，包含运行时依赖模块路径
4. 运行 perl Makefile.PL 配置
5. 运行 make -j1 编译
6. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G4 产物检查失败：bin/lib/include 均为空 | conanfile.py 中 build() 设置 `INSTALL_BASE={self.package_folder}` 且 package() 设置 `DESTDIR={self.package_folder}`，两者叠加导致路径嵌套 | build() 不设置 INSTALL_BASE，package() 仅使用 DESTDIR，安装后展平目录结构将 .pm 文件移到 lib/ 下 |
| 2 | 归档目录缺失 conanfile.py、conandata.yml、manifest.yaml 等关键文件 | finish 流程在 Step6 失败，归档未完成 | 手动从 conan 缓存恢复并修正 conanfile.py，创建完整的归档文件 |

## 源码修改

无补丁。纯 Perl 模块，源码无需任何修改即可在鸿蒙平台编译。

## 依赖版本

### 已存在
- perl 5.42.0: /data/service/hnp/bin/perl
- perl-moo 及其他运行时依赖: /storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.0

### 编译依赖
- perl（运行 Makefile.PL 和 make）

## 验证结果

```bash
# conan create 成功
conan create . -pr:h=ohos-aarch64
# → G2: PASS (conan create succeeded)
# → test_package: OK: SQL::Abstract smoke test passed
# → G4: PASS (lib/ 下找到 11 .pm 文件)

# conan-verify 全量检查
ohc-run.py conan-verify perl-sql-abstract 2.000001
# → G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS
# → L2: PASS | L4: PASS | L5: PASS
# → 可标记 status: published

# 上游测试套件
make test
# → 27 文件, 3932 测试, 24 PASS, 3 SKIP, 0 FAIL
# → Result: PASS

# 手动功能测试
perl -Iblib/lib sql_abstract_test.pl
# → 35 测试, 32 PASS, 2 设计行为, 1 SKIP
# → 通过率: 91% (核心功能 100%)
```

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/SQL/Abstract.pm | 113KB | 主模块 |
| lib/perl5/SQL/Abstract/Formatter.pm | 2.5KB | SQL 格式化器 |
| lib/perl5/SQL/Abstract/Parts.pm | 0.7KB | SQL 片段 |
| lib/perl5/SQL/Abstract/Plugin/BangOverrides.pm | 2.9KB | 插件 |
| lib/perl5/SQL/Abstract/Plugin/ExtraClauses.pm | 23KB | 扩展子句插件 |
| lib/perl5/SQL/Abstract/Reference.pm | 23KB | 引用文档 |
| lib/perl5/SQL/Abstract/Role/Plugin.pm | 1.3KB | 插件角色 |
| lib/perl5/SQL/Abstract/Test.pm | 12KB | 测试工具 |
| lib/perl5/SQL/Abstract/Tree.pm | 26KB | SQL 树形结构 |
| lib/perl5/DBIx/Class/SQLMaker/Role/SQLA2Passthrough.pm | 5.3KB | DBIC 集成 |
| lib/perl5/DBIx/Class/Storage/Debug/PrettyPrint.pm | 3.7KB | DBIC 调试 |

## 注意事项

1. 这是纯 Perl 模块，不需要 C 编译器或 CRT 链接修复（与 perl-dbd-pg 不同）
2. 运行时依赖的 Perl 模块（perl-moo 等）需提前安装到 PERL5LIB 路径
3. Perl EUMM 的 INSTALL_BASE 和 DESTDIR 参数不能设为同一路径，否则产生路径嵌套
4. Conan 的 package_info 应设置 PERL5LIB 环境变量供消费者使用

---
**编译结束**: 2026-07-03 04:24
**最终状态**: published (conan-verify 全部通过，上游测试 3932 PASS)
---
