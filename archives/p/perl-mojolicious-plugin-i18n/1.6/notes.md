# perl-mojolicious-plugin-i18n 1.6 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker)
- 编译日期: 2026-06-23
- 编译器: clang/clang++ (纯Perl模块，无需C编译)
- 状态: published

## 编译步骤

1. `perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local`
2. `make -j1`
3. `make test` — 5 tests, 124 subtests, all pass
4. `make install DESTDIR=$TEST_PREFIX` (staging)
5. `make install` (local install to ~/usr/local)
6. 验证: `perl -MMojolicious::Plugin::I18N -e 'print $Mojolicious::Plugin::I18N::VERSION'` → 1.6

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模式A自动构建报告"安装无产物" | 脚本检测产物时只查找二进制可执行文件，纯Perl模块仅安装.pm文件 | 切换模式B手动编译 |
| 2 | 下载URL在Savannah不存在 | 脚本搜索到的Savannah URL不正确 | 从BackPAN获取正确URL: https://backpan.perl.org/authors/id/S/SH/SHARIFULN/Mojolicious-Plugin-I18N-1.6.tar.gz |
| 3 | 归档缺少软件级manifest.yaml | 初始编译时未创建软件级元数据文件 | 已补充创建，包含software/description/category/versions等字段 |
| 4 | 测试报告过于简单 | 初始测试报告仅记录make test输出 | 已更新为详细功能测试报告，含10项测试+平台对比分析 |
| 5 | 缺少上库评估报告 | 初始归档无reviewer-report.md | 已创建，包含ARCHIVE-SPEC合规性检查和PR提交指引 |

## 源码修改

无补丁，纯Perl模块直接编译安装。

## 依赖版本

- Perl 5.42.0 (/data/service/hnp/perl.org/perl_5.42.0/)
- Mojolicious 9.42 (要求 >= 5)
- I18N::LangTags 0.45 (要求 >= 0.35)
- Test::More (测试依赖)

## 验证结果

### 官方测试套件
```bash
$ make test
t/i18n.t .................... ok
t/i18n_app.t ................ ok
t/i18n_lite_app.t ........... ok
t/i18n_shortcut_lite_app.t .. ok
t/i18n_url_for.t ............ ok
All tests successful.
Files=5, Tests=124,  7 wallclock secs
Result: PASS
```

### 模块加载验证
```bash
$ perl -MMojolicious::Plugin::I18N -e 'print "Version: ", $Mojolicious::Plugin::I18N::VERSION, "\n"'
Version: 1.6
```

### 自定义功能测试 (52项，全部通过)
- 多语言翻译: 英/中/日/德 ✅
- Accept-Language 检测 ✅
- URL 语言切换 (/en /zh /ja) ✅
- 手动语言切换 ✅
- 语言回退机制 ✅
- 不支持语言返回 404 ✅
- 模块文件完整性 ✅
- 依赖版本满足要求 ✅

## 质量门禁结果

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建 | ✅ PASS | 无补丁, 自包含 |
| G1 二进制完整性 | ✅ PASS | 无二进制文件 |
| G2 功能可用性 | ✅ PASS | ⚠️ 1 (staging 警告) |
| G3 可移植性 | ✅ PASS | 无 RPATH 需求 |
| G4 档案完整性 | ✅ PASS | 文件结构完整 |

## 与 perl-dbd-pg 编译经验对比

| 维度 | perl-dbd-pg 3.18.0 | perl-mojolicious-plugin-i18n 1.6 |
|------|-------------------|----------------------------------|
| 模块类型 | XS (C 扩展) | 纯 Perl |
| 补丁数量 | 2 个 | 0 个 |
| SELinux 限制 | ❌ 有 (.so 加载受限) | ✅ 无 |
| 运行时依赖 | PostgreSQL libpq | 无 |
| 可用性 | 需管理员安装 | 直接可用 |

**关键差异**: perl-dbd-pg 因 XS 模块受 SELinux HMDFS 限制需管理员安装到系统目录，而 perl-mojolicious-plugin-i18n 作为纯 Perl 模块完全不受此限制，编译安装后即可直接使用。

## 注意事项

- 这是纯Perl模块，无C/XS代码，编译过程简单
- 模式A自动构建脚本对纯Perl模块的产物检测有局限性，需使用模式B手动编译
- 安装产物路径: lib/site_perl/5.42.0/Mojolicious/Plugin/I18N.pm
- 上库评估: ✅ 符合 ARCHIVE-SPEC v2.0 要求，建议提交 PR
---

**编译结束**: 2026-06-23
**最终状态**: published
**上库评估**: ✅ 符合上库要求 (详见 reports/reviewer-report.md)
