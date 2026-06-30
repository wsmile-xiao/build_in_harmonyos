# perl-locale-codes 3.85-r0 编译笔记

## 编译环境
- Perl 版本: 5.42.0
- 构建系统: MakeMaker (Perl标准)
- 源码来源: CPAN (Locale-Codes-3.85.tar.gz)
- 编译日期: 2026-06-15
- 状态: built

## 编译步骤

### 1. 源码获取
```bash
源码位于: Locale-Codes-3.85.tar.gz
URL: https://cpan.metacpan.org/authors/id/S/SB/SBECK/Locale-Codes-3.85.tar.gz
```

### 2. 配置
```bash
cd ~/tmp/builds/perl-locale-codes-3.85-r0.work
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
```
- 配置成功
- 纯 Perl 模块，无 C 代码

### 3. 编译
```bash
make
```
- 编译成功
- 纯 Perl 模块，无二进制编译
- 所有 .pm 和 .pod 文件复制到 blib 目录

### 4. 测试依赖安装
由于原始测试跳过（缺少 Test::Inter），我们安装了测试依赖：
```bash
cd ~/tmp
wget https://cpan.metacpan.org/authors/id/S/SB/SBECK/Test-Inter-1.09.tar.gz
tar xzf Test-Inter-1.09.tar.gz
cd Test-Inter-1.09
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
make && make install
```

### 5. 测试
```bash
cd ~/tmp/builds/perl-locale-codes-3.85-r0.work
export PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0
make test
```
- **结果**: PASS
- 测试文件: 22
- 测试数: 1230
- 全部通过

### 6. 安装 (Staging)
```bash
make install DESTDIR=~/tmp/test-install-perl-locale-codes-3.85-r0
```
- 安装成功
- 所有文件安装到 `~/tmp/test-install-perl-locale-codes-3.85-r0/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/Locale/`

### 7. 本地安装验证
```bash
make install
```
- 安装到 `~/usr/local/lib/site_perl/5.42.0/Locale/`
- 使用 PERL5LIB 环境变量验证模块可用

### 8. 预编译包制作
```bash
cd ~/tmp/test-install-perl-locale-codes-3.85-r0/storage/Users/currentUser/usr/local
tar -czf perl-locale-codes-3.85-r0-ohos-aarch64.tar.gz lib/
```
- 包大小: 2.2M
- 内容: lib/site_perl/5.42.0/Locale/ 目录及其所有子模块

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试跳过（缺少 Test::Inter） | 原始编译未安装测试依赖 | 从 CPAN 安装 Test::Inter 1.09 |
| 2 | 手动验证不够全面 | 缺少自动化测试 | 参考 perl-dbd-pg 测试报告格式 |
| 3 | manifest.yaml 缺少必填字段 | 未按 ARCHIVE-SPEC.md 规范 | 补充 source.url 等字段 |

## 功能验证结果

### 单元测试
- Files: 22
- Tests: 1230
- Result: PASS

### 功能测试 (33项)
| 模块 | 测试项 | 结果 |
|------|--------|------|
| Locale::Codes | 模块加载 | ✅ PASS |
| Locale::Country | code2country/country2code | ✅ PASS |
| Locale::Language | code2language/language2code | ✅ PASS |
| Locale::Currency | code2currency/currency2code | ✅ PASS |
| Locale::Script | code2script/script2code | ✅ PASS |
| 数据完整性 | all_*_codes() | ✅ PASS |

### 数据统计
- 国家代码: 249 条
- 语言代码: 185 条
- 货币代码: 177 条
- 脚本代码: 223 条

## 与 perl-dbd-pg 编译经验对比

| 特性 | perl-dbd-pg | perl-locale-codes |
|------|-------------|-------------------|
| 模块类型 | XS + C代码 | 纯 Perl |
| SELinux限制 | HMDFS无法加载XS | ✅ 无限制 |
| 特殊链接参数 | 需要 | ❌ 不需要 |
| 管理员安装 | 必需 | ❌ 不需要 |
| 即用性 | 需等待管理员 | ✅ 立即可用 |

## 模块内容
安装的 Perl 模块包括：
- Locale::Codes (核心模块)
- Locale::Country (国家代码 - ISO 3166)
- Locale::Language (语言代码 - ISO 639)
- Locale::Currency (货币代码 - ISO 4217)
- Locale::Script (脚本代码 - ISO 15924)
- Locale::Codes::* (各种代码表和辅助模块)

## 质量门禁结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| G1 二进制完整性 | PASS | 无二进制文件 |
| G2 功能可用性 | PASS | 33/33 功能测试通过 |
| G3 可移植性 | PASS | 纯 Perl，无平台依赖 |
| G4 档案完整性 | PASS | 所有必填字段完整 |

## 最终状态
- status: published
- ✅ 编译成功
- ✅ 测试全部通过 (1230 + 33)
- ✅ 预编译包已制作
- ✅ 功能验证通过
- ✅ 已发布到 cmd-pkgs
- ⚠️ 用户需配置 PERL5LIB 环境变量

---
编译结束时间: 2026-06-15 15:10
编译总耗时: 约5分钟（含测试依赖安装）
---

**编译结束**: 2026-06-15 15:10
**最终状态**: published
**测试结果**: PASS (单元测试 1230/1230 + 功能测试 33/33)
**发布日期**: 2026-06-15
**用户配置**: 需设置 PERL5LIB=~/usr/local/lib/site_perl/5.42.0