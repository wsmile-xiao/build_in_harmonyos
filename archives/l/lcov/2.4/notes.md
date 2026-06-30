# lcov 2.4 编译笔记

## 编译过程

lcov 是纯 Perl 脚本工具，无需编译。安装步骤：
```bash
make install PREFIX=/storage/Users/currentUser/usr/local DESTDIR=~/tmp/test-install-lcov-2.4
```

## Perl 模块依赖问题

### 原始依赖
lcov 源码需要以下 Perl 模块：
- Capture::Tiny
- DateTime
- Digest::MD5（核心模块）
- JSON
- Date::Parse

### 问题分析
DateTime 模块有大量依赖（DateTime::TimeZone、DateTime::Locale 等），安装耗时且复杂。
OpenHarmony 平台没有预编译的 DateTime 模块包。

### 解决方案
使用 Perl 核心模块 Time::Piece 替代 DateTime：
- Time::Piece 是 Perl 5.42 的核心模块，无需额外安装
- 提供基本的时间日期功能，足以满足 lcov 的需求

### 修改内容

#### lcovutil.pm
1. `use DateTime;` → `use Time::Piece;`
2. `DateTime::Format::W3CDTF->parse_datetime()` → 本地实现
3. `DateTime->new(year=>..., month=>..., ...)` → `Time::Piece->strptime()`

#### genhtml
1. `use DateTime;` → `use Time::Piece;`
2. `DateTime->from_epoch(epoch => $epoch)` → `localtime($epoch)`
3. `DateTime->now()` → `localtime()`

## 验证结果

### 测试命令
```bash
# lcov
lcov --version
# 输出: lcov: LCOV version 2.4

# genhtml
genhtml --version
# 输出: genhtml: LCOV version 2.4
```

### 功能测试
lcov 和 genhtml 基本功能正常：
- 版本查询 ✅
- 帮助信息 ✅
- 基本参数解析 ✅

## 安装的 Perl 模块

用户需要安装以下模块（已通过 cmd-pkgs 或手动安装）：
- Capture::Tiny (0.48)
- JSON (4.10)
- Try::Tiny (0.31)
- Date::Parse (来自 TimeDate 2.33)

## 补丁文件

| 补丁文件 | 说明 |
|----------|------|
| 0001-replace-DateTime-with-Time-Piece-lcovutil.patch | 修改 lcovutil.pm，用 Time::Piece 替代 DateTime |
| 0002-replace-DateTime-with-Time-Piece-genhtml.patch | 修改 genhtml，用 localtime 替代 DateTime |

## 本次修复过程（2026-05-20）

### 问题
上次 PR 的预编译包没有应用补丁，导致运行验证失败（缺少 DateTime 模块）。

### 修复步骤
1. **重新安装补丁版本**: 从已应用补丁的源码重新安装 lcov 到 ~/usr/local/
2. **安装 Perl 模块**: 使用 cpan 安装 Capture::Tiny、JSON、Try::Tiny、Date::Parse 到 ~/perl_local/lib/perl5/
3. **验证功能**: 设置 PERL5LIB 环境变量后，lcov 和 genhtml 能正常运行
4. **制作预编译包**: 制作包含 Perl 模块的预编译包
5. **修改 lcovutil.pm**: 在 lcovutil.pm 开头添加 BEGIN 块，设置 Perl 模块路径

### 验证结果
```bash
export PERL5LIB=/storage/Users/currentUser/perl_local/lib/perl5:$PERL5LIB
lcov --version  # 输出: lcov: LCOV version 2.4-beta ✅
genhtml --version  # 输出: genhtml: LCOV version 2.4-beta ✅
```

### 预编译包内容
预编译包 `lcov-2.4-ohos-aarch64.tar.gz` 包含：
- bin/: lcov、genhtml、geninfo、genpng、gendesc 等工具
- lib/lcov/: lcovutil.pm（已应用补丁并添加 Perl 模块路径）
- share/lcov/: 支持脚本
- perl-modules/: Capture::Tiny、JSON、Try::Tiny、Date::Parse 等模块

### 用户使用指南
1. 解压预编译包到目标目录
2. 设置环境变量：`export PERL5LIB=/目标目录/perl-modules:$PERL5LIB`
3. 运行 lcov 或 genhtml

## 后续建议

1. **cmd-pkgs 扩展**: 可以将 Capture::Tiny、JSON、Try::Tiny、TimeDate 等模块添加到 cmd-pkgs
2. **Perl 模块管理**: 建议开发 Perl 模块的预编译包管理系统
3. **测试覆盖**: 建议添加更完整的功能测试（如覆盖率收集和报告生成）
4. **安装脚本**: 建议创建安装脚本，自动设置 PERL5LIB 环境变量