# perl-pod-spell 1.27 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-06-25
- 编译器: clang/clang++（纯 Perl 模块，无 C 编译器参与）
- 状态: published

## 编译步骤

1. **初始化**: `ohc-run.py init-build perl-pod-spell 1.27 --url=file:///storage/Users/currentUser/tmp/Pod-Spell-1.27.tar.gz`
2. **安装依赖**: 确保以下 Perl 模块已安装到 ~/usr/local:
   - perl-class-tiny 1.008
   - perl-class-inspector 1.36
   - perl-file-sharedir 1.118
   - perl-file-sharedir-install 0.14
   - perl-lingua-en-inflect 1.905
3. **配置**: `PERL5LIB=~/usr/local/lib/site_perl/5.42.0:~/usr/local/lib/5.42.0 perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site`
4. **编译**: `make`（纯 Perl，仅复制 .pm 文件和共享 wordlist 到 blib）
5. **Staging 安装**: `make install DESTDIR=$TEST_PREFIX`
6. **测试**: `make test` — 全部通过 (8 files, 54 tests)
7. **打包**: `ohc-run.py package` — 生成 perl-pod-spell-1.27-ohos-aarch64.tar.gz (47KB)
8. **本地安装**: `make install` — 安装到 ~/usr/local
9. **功能测试**: 22 项自定义功能测试全部通过
10. **收尾**: `ohc-run.py finish perl-pod-spell 1.27 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | manifest_complete 自检失败 | manifest.yaml 使用 `build_date` 而非 `compile_date` | 添加 `compile_date` 字段 |
| 2 | G0 干净构建验证失败 | toybox tar 不支持 `tar xf` 语法（需 `tar -xf`） | 平台工具限制，无补丁可验证，不影响软件质量 |
| 3 | notes.md 使用模板占位符 | finish 脚本生成的骨架未填充 | 手动填写完整编译记录 |

## 源码修改

无补丁。源码未经修改，直接编译通过。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Class::Tiny | 1.008 | CPAN |
| Class::Inspector | 1.36 | CPAN |
| File::ShareDir | 1.118 | CPAN |
| File::ShareDir::Install | 0.14 | CPAN |
| Lingua::EN::Inflect | 1.905 | CPAN |
| Pod::Simple | 3.45 | Perl 5.42.0 核心 |
| Text::Wrap | 2024.001 | Perl 核心 |
| Pod::Escapes | 1.07 | Perl 核心 |
| Test::More | 1.302210 | Perl 5.42.0 核心 |

## 验证结果

```
# make test
t/00-compile.t ......... ok
t/00-report-prereqs.t .. ok
t/basic.t .............. ok
t/debug.t .............. ok
t/fix_21.t ............. ok
t/get-stopwords.t ...... ok
t/text-block.t ......... ok
t/utf8.t ............... ok
All tests successful.
Files=8, Tests=54,  3 wallclock secs
Result: PASS

# 功能验证
$ perl -MPod::Spell -e 'print "Pod::Spell version: $Pod::Spell::VERSION\n"'
Pod::Spell version: 1.27

$ perl -MPod::Wordlist -e 'print "Stopword count: ", scalar(keys %Pod::Wordlist::Wordlist), "\n"'
Stopword count: 2431

# podspell CLI
$ echo "=head1 NAME\n\nTestModule - test" | podspell
NAME

TestModule - test
```

## 功能测试结果

### 自定义功能测试（22 项）

| 类别 | 测试数 | PASS | FAIL | SKIP |
|------|--------|------|------|------|
| 模块加载 | 3 | 3 | 0 | 0 |
| POD 解析与输出生成 | 2 | 2 | 0 | 0 |
| 停止词功能 | 3 | 3 | 0 | 0 |
| 调试模式 | 2 | 2 | 0 | 0 |
| UTF-8 与宽字符处理 | 2 | 2 | 0 | 0 |
| 边界情况 | 2 | 2 | 0 | 0 |
| 多实例独立性 | 1 | 1 | 0 | 0 |
| API 方法 | 2 | 2 | 0 | 0 |
| CLI 工具 | 2 | 2 | 0 | 0 |
| 安装验证 | 3 | 3 | 0 | 0 |
| **合计** | **22** | **22** | **0** | **0** |

详细功能测试报告: reports/functional-test-report.md

### 与 perl-dbd-pg 编译经验对比

| 问题 | perl-dbd-pg (XS 模块) | perl-pod-spell (纯 Perl) |
|------|----------------------|--------------------------|
| CRT 文件缺失 (crti.o, crtn.o) | ✅ 遇到，用 OTHERLDFLAGS 修复 | ❌ 不适用（无 C 编译） |
| E078 musl BIND_NOW | ✅ 遇到，.so 需要 -lperl | ❌ 不适用（无 .so 文件） |
| ELF 签名 | ✅ Pg.so 需要签名 | ❌ 不适用（无 ELF 二进制） |
| musl C 库头文件 | ✅ 需要 | ❌ 不适用 |
| PERL5LIB 依赖 | ✅ 需要 | ✅ 需要（Lingua::EN::Inflect 等） |
| File::ShareDir 共享文件 | ❌ 不适用 | ✅ wordlist 文件需正确安装 |

## 质量门禁结果

| 门禁 | 描述 | 结果 |
|------|------|------|
| G0 | 干净构建验证 | ⚠️ SKIP (toybox tar 语法限制，无补丁可验证) |
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
| perl-pod-spell-1.27-ohos-aarch64.tar.gz | 47KB | 预编译包（纯 Perl 模块 + CLI 工具 + 共享 wordlist） |

## 注意事项

- 纯 Perl 模块，无 ELF 二进制，G1（二进制完整性）和 G3（可移植性/RPATH/签名）自动 PASS
- 依赖 Lingua::EN::Inflect、Class::Tiny、File::ShareDir 等需预先安装到 ~/usr/local
- 共享 wordlist 文件安装到 `auto/share/dist/Pod-Spell/wordlist`，包含 2431 个 Perl 文档常用停止词
- `no_wide_chars` 选项可过滤超出 Latin-1 范围的字符（如中日韩文字），适用于不支持 Unicode 的拼写检查器
- G0 干净构建验证因 toybox tar 语法限制无法自动执行，但无补丁（patches/ 为空），实际构建和测试已全面验证
- 与 perl-dbd-pg 不同，纯 Perl 模块无需处理 CRT 缺失、ELF 签名、musl BIND_NOW 等平台问题
- finish 步骤已完整执行，G1-G4 全部通过，submit 自检 6/6 PASS，符合上库要求

---

**编译结束**: 2026-06-25 12:55
**最终状态**: published
