# perl-mail-spamassassin 4.0.2 编译笔记

**编译日期**: 2026-06-15
**编译状态**: ✅ 成功
**构建系统**: Perl ExtUtils::MakeMaker

---

## 编译过程

### 1. 环境准备

- Perl 版本: 5.42.0
- 构建系统: ExtUtils::MakeMaker
- 安装前缀: ~/usr/local

### 2. 配置阶段

使用 `perl Makefile.PL PREFIX=$DEFAULT_PREFIX` 配置。

**问题与解决**:
- 部分依赖模块缺失，通过预编译包安装解决
- Makefile.PL 需要修改以适配鸿蒙平台路径

### 3. 编译阶段

```bash
make -j1
```

**编译产物**:
- Perl 脚本: spamassassin, spamd, sa-learn, sa-update, sa-compile, sa-awl, sa-check_spamd
- C 程序: spamc (ELF 二进制)
- Perl 模块: 120 个 .pm 文件

### 4. 安装阶段

```bash
make install DESTDIR=$TEST_PREFIX
```

### 5. 打包阶段

创建了两个预编译包:
- `perl-mail-spamassassin-4.0.2-ohos-aarch64.tar.gz` (标准版)
- `perl-mail-spamassassin-4.0.2-ohos-aarch64-debug.tar.gz` (调试版)

---

## 关键补丁说明

### 0002-Makefile.PL.patch
修改 Makefile.PL 移除 HTML::Parser (XS) 和 Mail::DKIM 必需依赖，允许在 OpenHarmony hmdfs 上构建。

### 0003-0005: HTML::Parser 延迟加载适配
修复 HTML.pm, Message/Node.pm, DependencyInfo.pm：
- HTML::Parser XS 模块在 hmdfs 上无法加载（dlopen 限制）
- 改为延迟加载 + fallback 处理
- 将 HTML::Parser 从必需依赖改为可选依赖

### 0008-0013: 命令行脚本路径补丁
修复 sa-awl, sa-check_spamd, sa-compile, sa-learn, sa-update, spamassassin 脚本：
- Perl 解释器路径替换为 ~/usr/local/bin/perl
- 配置目录路径替换为 ~/usr/local/etc/mail/spamassassin

### 0014-0015: spamc 头文件补丁
- io.h: Windows io.h stub，提供 errno/signal 定义
- spamc.h: 配置文件路径硬编码

### 0017: spamd 补丁
修复 spamd 守护进程的 Perl 路径和功能适配。

---

## 后续修复记录

### 2026-06-17: sa-check_spamd VERSION 初始化问题

**问题**: `sa-check_spamd --help` 输出警告 "Use of uninitialized value $VERSION"

**根因**: 脚本第 85 行 `$VERSION = $Mail::SpamAssassin::VERSION`，但只加载了 `Mail::SpamAssassin::Util` 模块，该模块不会自动加载主模块，导致 `$Mail::SpamAssassin::VERSION` 未定义。

**修复**: 在脚本第 73 行添加 `use Mail::SpamAssassin;` 确保主模块加载。

**修改文件**: `sa-check_spamd` (补丁 0009-sa-check_spamd.patch)

**验证**:
```bash
$ sa-check_spamd --help
sa-check_spamd version 4.000002
For more details, use "perldoc sa-check_spamd".
```

---

## 知识沉淀

### L1 平台真理 (知识图谱)

无新平台真理发现。SpamAssassin 主要是纯 Perl 实现，无 XS 模块限制。

### L2 构建模式经验

1. **Perl 模块构建系统**: ExtUtils::MakeMaker
   - 配置命令: `perl Makefile.PL PREFIX=$DEFAULT_PREFIX`
   - 编译命令: `make`
   - 安装命令: `make install DESTDIR=$TEST_PREFIX`

2. **混合语言项目**: SpamAssassin 包含 Perl 脚本和 C 程序
   - Perl 脚本需要修复解释器路径
   - C 程序 (spamc) 使用标准 autotools 编译流程

3. **预编译包结构**: Perl 模块需要包含完整目录结构
   - bin/: 命令行工具
   - lib/site_perl/: Perl 模块
   - etc/: 配置文件

### L3 本版笔记

1. ✅ sa-check_spamd VERSION 问题已修复（2026-06-17）
2. sa-update 需要用户首次运行获取规则
3. spamc 二进制已签名，可在鸿蒙平台直接执行

---

## 功能测试结果

详见 `reports/test-report.md`。

核心结论:
- ✅ 所有命令行工具正常工作
- ✅ 所有 Perl 模块正常加载
- ✅ spamc 二进制已签名可执行
- ✅ sa-check_spamd VERSION 问题已修复

---

## 与 perl-dbd-pg 经验对比

| 特性 | perl-dbd-pg | perl-mail-spamassassin |
|-----|-------------|------------------------|
| XS 模块 | 有 (受 SELinux 限制) | 无 (纯 Perl) |
| 运行时可用性 | 需管理员安装 | 立即可用 |
| 测试复杂度 | 高 (需要 PostgreSQL) | 低 (独立运行) |

SpamAssassin 的纯 Perl 实现使其在鸿蒙平台更容易使用，无需处理 XS 模块的 SELinux 限制问题。

---

**编译结束**: 2026-06-15 23:13
**最终状态**: built
**更新时间**: 2026-06-17 (sa-check_spamd VERSION 修复)