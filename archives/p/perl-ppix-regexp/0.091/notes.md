# perl-ppix-regexp 0.091 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (perl-eumm)
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-ppix-regexp 0.091`
2. 读取上下文：`source .build-context-perl-ppix-regexp-0.091`
3. 设置环境变量：
   ```bash
   export PERL5LIB=$DEFAULT_PREFIX/lib/site_perl/5.42.0:$DEFAULT_PREFIX/lib/perl5/site_perl:$DEFAULT_PREFIX/lib/perl5:$PERL5LIB
   export PERL_PARAMS_UTIL_PP=1
   ```
4. 编译安装：
   ```bash
   cd $BUILD_SRC_DIR
   perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site
   make -j1
   make install DESTDIR=$TEST_PREFIX
   make install  # 安装到实际 prefix
   ```
5. 测试：`make test` — 13264 tests PASS
6. Conan 配方：`python3 $SKILL_ROOT/scripts/ohc-run.py conan-init perl-ppix-regexp 0.091`
7. 验证：`python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-ppix-regexp 0.091`
8. 收尾：`python3 $SKILL_ROOT/scripts/ohc-run.py finish perl-ppix-regexp 0.091 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package Parse test: FAIL | test_package 使用 `qr/foo/` (Regexp 引用) 调用 `PPIx::Regexp::Lexer->new()`。Tokenizer::new() 对非 PPI::Element 的 ref 对象返回 undef + errstr "Regexp not supported"。这是 PPIx::Regexp 的设计限制。 | 将 `qr/foo/` 改为字符串形式 `"qr/foo/"`。同时增加严格失败检查（之前 FAIL 未被捕获导致 conan-verify 误标 PASS）。 |
| 2 | finish 命令失败 (exit_reason: finish_knowledge_required) | knowledge gap 未处理 | 重新执行 conan-verify 后 finish 正常通过 |
| 3 | Params::Util XS .so 无法 dlopen | HMDFS 上 SELinux 限制 .so 动态加载 | 设置 `PERL_PARAMS_UTIL_PP=1` 使用纯 Perl 回退模式 |
| 4 | notes.md 为模板占位符 | 子任务未填写实际内容 | 手动填写完整编译笔记 |

## 源码修改

无源码补丁。仅修改了归档中的 test_package/conanfile.py（非源码文件）。

### test_package/conanfile.py 修改详情
- 将 `PPIx::Regexp::Lexer->new(qr/foo/)` 改为 `PPIx::Regexp::Lexer->new("qr/foo/")`
- 增加严格失败检查：parse test 失败时 raise Exception（之前仅打印 warning）
- 新增 Test 3 (复杂正则解析) 和 Test 4 (Dumper 功能)

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Perl | 5.42.0 | 系统内置 (/data/service/hnp/bin/perl) |
| PPI | 1.284 | 预编译安装 (perl-ppi 归档) |
| Params::Util | 系统自带 | PERL_PARAMS_UTIL_PP=1 纯 Perl 模式 |
| clang | 15.0.4 | /data/service/hnp/bin/clang |

## 验证结果

```bash
# make test
All tests successful.
Files=10, Tests=13264,  5 wallclock secs
Result: PASS

# conan-verify (G0-G4 + L2/L4/L5)
G0: PASS  G1: PASS  G2: PASS  G3: PASS  G4: PASS
L2: PASS  L4: PASS  L5: PASS (67 个文件基线一致)

# 功能测试 (8项全部通过)
PPIx::Regexp version: 0.091
Parse test: OK
Complex parse test: OK
Dumper test: OK
```

## 注意事项

1. **PPIx::Regexp::Tokenizer 不接受 qr// 对象**：必须使用字符串形式如 `"qr/foo/"`、`"m/foo/i"`、`"s/foo/bar/g"` 传入。这是模块设计限制，非平台问题。
2. **PERL_PARAMS_UTIL_PP=1 必须设置**：Params::Util 的 XS .so 在 HMDFS 上无法 dlopen（SELinux 限制），需使用纯 Perl 回退模式。
3. **PERL5LIB 必须包含 PPI 安装路径**：`$DEFAULT_PREFIX/lib/site_perl/5.42.0`
---

**编译结束**: 2026-06-26 14:46
**最终状态**: published
