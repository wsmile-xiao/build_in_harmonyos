# perl-pod-coverage 0.23 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-06-24
- 编译器: clang/clang++（纯 Perl 模块，无 C 编译器参与）
- 状态: published

## 编译步骤

1. **安装依赖**: 下载并编译安装 Devel::Symdump 2.18 和 Pod::Parser 1.67 到 ~/usr/local
   - `perl Makefile.PL PREFIX=$DEFAULT_PREFIX && make && make install`
2. **配置**: `PERL5LIB=~/usr/local/lib/site_perl/5.42.0:~/usr/local/lib/5.42.0 perl Makefile.PL PREFIX=$DEFAULT_PREFIX`
3. **编译**: `make`（纯 Perl，仅复制 .pm 文件到 blib）
4. **Staging 安装**: `make install DESTDIR=$TEST_PREFIX`
5. **测试**: `make test` — 全部通过
6. **打包**: `ohc-run.py package` — 生成 perl-pod-coverage-0.23-ohos-aarch64.tar.gz (31KB)
7. **本地安装**: `make install` — 安装到 ~/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 URL 404 | savannah.nongnu.org 上该文件不存在 | 改用 CPAN backpan URL: https://backpan.perl.org/authors/id/R/RC/RCLAMP/Pod-Coverage-0.23.tar.gz |
| 2 | SSL 证书验证失败 | Python urllib 无法验证 backpan SSL 证书 | 手动用 curl -kL 下载，使用 --no-download 初始化 |
| 3 | Perl 模块依赖缺失 | Devel::Symdump 和 Pod::Parser 未安装 | 从 MetaCPAN 下载并编译安装到 ~/usr/local |
| 4 | Perl @INC 不包含 ~/usr/local | Perl 安装在 /data/service/hnp，@INC 不含用户路径 | 设置 PERL5LIB 环境变量 |
| 5 | manifest G4 检查失败 | manifest.yaml 缺少顶层 build_system 字段 | 添加 `build_system: perl` 到 manifest |

## 源码修改

无补丁。源码未经修改，直接编译通过。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Devel::Symdump | 2.18 | MetaCPAN (A/AN/ANDK) |
| Pod::Parser (含 Pod::Find) | 1.67 | MetaCPAN (M/MA/MAREKR) |
| Test::More | 1.302210 | Perl 5.42.0 核心 |

## 验证结果

```
# make test
t/01compile.t ..... ok
t/02simple.t ...... ok
t/03import.t ...... ok
t/04cvgv.t ........ ok
t/05parentage.t ... ok
t/06trustme.t ..... ok
t/07pod.t ......... skipped: Test::Pod 1.00 required for testing POD
t/08tie.t ......... ok
t/09whitespace.t .. ok
All tests successful.
Files=9, Tests=69, 2 wallclock secs
Result: PASS

# 功能验证
$ perl -MPod::Coverage -e 'print $Pod::Coverage::VERSION, "\n"'
0.23

$ perl -MPod::Coverage -e '
my $pc = Pod::Coverage->new(package => "Pod::Coverage");
print "Coverage: ", $pc->coverage, "\n";'
Coverage: 1
```

## 功能测试结果

### 自定义功能测试（20 项）

| 类别 | 测试数 | PASS | FAIL | SKIP |
|------|--------|------|------|------|
| 模块加载 | 1 | 1 | 0 | 0 |
| 核心覆盖率 API | 6 | 6 | 0 | 0 |
| 构造参数 (trustme/private) | 2 | 2 | 0 | 0 |
| also_private 参数 | 1 | 1 | 0 | 0 |
| 边界情况 | 3 | 3 | 0 | 0 |
| 多实例 | 1 | 1 | 0 | 0 |
| 子模块 (CountParents/ExportOnly/Overloader) | 3 | 3 | 0 | 0 |
| Staging 安装验证 | 1 | 1 | 0 | 0 |
| 预期边界情况 | 2 | 0 | 0 | 2 |
| **合计** | **20** | **18** | **0** | **2** |

### CLI 工具测试

```
$ cd Pod-Coverage-0.23 && pod_cover Pod::Coverage
Pod::Coverage has a doc coverage of 100%.
Pod::Coverage::ExportOnly has a doc coverage of 0%.
Pod::Coverage::Overloader has a doc coverage of 0%.
Pod::Coverage::CountParents has a doc coverage of 0%.
Summary: 8 total, 7 covered, 1 uncovered, 87.5% coverage
```

### 平台兼容性评估

| 检查项 | 状态 |
|--------|------|
| Perl 模块加载（纯 Perl，无 XS） | ✅ 无 E078 (musl BIND_NOW) |
| 对象实例化和方法调用 | ✅ 全部正常 |
| 符号枚举 (covered/uncovered/naked) | ✅ 正常 |
| 覆盖率计算（浮点运算） | ✅ 精确 |
| 多对象实例 | ✅ 无干扰 |
| CLI 工具 (pod_cover) | ✅ 从源码目录运行正常 |
| 子模块加载 | ✅ 全部加载成功 |
| Staging DESTDIR 安装 | ✅ 正确加载 |
| 本地 ~/usr/local 安装 | ✅ 正确加载 |

### 预期边界情况（非缺陷）

1. **pod_cover 无 MANIFEST 时失败**: 按设计，pod_cover 需从包含 MANIFEST 的发行版源码目录运行
2. **ExportOnly 对 Pod::Coverage 返回 undef**: 按设计，ExportOnly 仅检查 @EXPORT/@EXPORT_OK 符号，Pod::Coverage 是 OO 模块无导出

详细功能测试报告: reports/functional-test-report.md

### 与 perl-dbd-pg 编译经验对比

| 问题 | perl-dbd-pg (XS 模块) | perl-pod-coverage (纯 Perl) |
|------|----------------------|------------------------------|
| CRT 文件缺失 (crti.o, crtn.o) | ✅ 遇到，用 OTHERLDFLAGS 修复 | ❌ 不适用（无 C 编译） |
| E078 musl BIND_NOW | ✅ 遇到，.so 需要 -lperl | ❌ 不适用（无 .so 文件） |
| ELF 签名 | ✅ Pg.so 需要签名 | ❌ 不适用（无 ELF 二进制） |
| musl C 库头文件 | ✅ 需要 | ❌ 不适用 |
| PERL5LIB 依赖 | ✅ 需要 | ✅ 需要（Devel::Symdump, Pod::Parser） |

## 质量门禁结果

| 门禁 | 描述 | 结果 |
|------|------|------|
| G0 | 干净构建验证 | ✅ PASS |
| G1 | 二进制完整性 | ✅ PASS（0 二进制，纯 Perl） |
| G2 | 功能可用性 | ✅ PASS |
| G3 | 可移植性（RPATH/签名） | ✅ PASS（无 ELF，N/A） |
| G4 | 档案完整性 | ✅ PASS |

### Submit 自检（6/6 PASS）

| 检查项 | 结果 |
|--------|------|
| manifest_complete | ✅ PASS |
| progress_closed | ✅ PASS |
| patches_valid | ✅ PASS |
| packaging_present | ✅ PASS |
| no_temp_files | ✅ PASS |
| test_report_present | ✅ PASS |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-pod-coverage-0.23-ohos-aarch64.tar.gz | 31KB | 预编译包（纯 Perl 模块） |

## 注意事项

- 纯 Perl 模块，无 ELF 二进制，G1（二进制完整性）和 G3（可移植性/RPATH/签名）自动 PASS
- 依赖 Devel::Symdump 和 Pod::Parser 需预先安装到 ~/usr/local，并通过 PERL5LIB 提供给构建和测试
- t/07pod.t 跳过（需要 Test::Pod 1.00，未安装），不影响功能验证
- DESTDIR 模式：PREFIX=$DEFAULT_PREFIX + DESTDIR=$TEST_PREFIX，产物安装到 $TEST_PREFIX/$DEFAULT_PREFIX/
- 与 perl-dbd-pg 不同，纯 Perl 模块无需处理 CRT 缺失、ELF 签名、musl BIND_NOW 等平台问题
- finish 步骤已完整执行，G0-G4 全部通过，submit 自检 6/6 PASS，符合上库要求

---

**编译结束**: 2026-06-24 19:34
**最终状态**: published
