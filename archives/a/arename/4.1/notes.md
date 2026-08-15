# arename v4.1 适配笔记

## 软件信息
- 名称: arename
- 版本: 4.1
- 语言: Perl (脚本工具)
- 构建系统: Makefile
- 上游: https://github.com/ft/arename
- 类型: 命令行工具（Perl脚本），非C/C++库

## 编译过程

### Step 1: genperlscripts
- 命令: `PERL=/data/service/hnp/bin/perl make genperlscripts`
- 结果: 成功
- 说明: 从 .in 模板生成 Perl 脚本和模块，替换 @@perl@@ 和 @@arenameversioninfo@@

### Step 2: install
- 命令: `make install prefix=$TEST_PREFIX`
- 结果: 成功（需修改 install.sh）
- 说明: 安装 arename、ataglist 脚本到 bin/，Perl 模块到 lib/site_perl/

### Step 3: install-doc
- 命令: `make install-doc prefix=$TEST_PREFIX`
- 结果: 成功
- 说明: 安装文档到 share/doc/arename/ 和 man pages

## 修改记录

### 1. install.sh - chown 兼容性修复
- 文件: bin/install.sh
- 原因: OHOS 平台无 chown 命令（SELinux 限制）
- 修改: 将 `chown root:root ... || exit 1` 改为 `chown root:root ... 2>/dev/null || true`
- 影响: 两处 chown 调用

### 2. PERL 路径
- 默认 Makefile 中 PERL=/usr/bin/perl
- OHOS 上 Perl 路径: /data/service/hnp/bin/perl
- 通过环境变量 PERL 传递给 genperlscripts

## 运行时依赖（非构建依赖）
- Readonly (CPAN 模块, 纯 Perl)
- Audio::Scan (CPAN 模块, XS 扩展, 需要 C 编译)
- 其他所有 use 语句均为 Perl 核心模块（Carp, Data::Dumper, English, Getopt::Long, File::Basename, File::Copy, Cwd, Term::ANSIColor, Encode, File::stat, File::Spec, Exporter）

## 构建产物
- bin/arename (Perl 脚本, 60KB)
- bin/ataglist (Perl 脚本, 3KB)
- lib/site_perl/ARename.pm 及子模块
- share/doc/arename/ 文档
- share/man/man1/ 手册页

## Conan 配方注意事项
- 这是 Perl 脚本工具，非 C/C++ 编译
- build() 方法需要: make genperlscripts PERL=... && make install prefix=...
- 需要补丁修复 install.sh 的 chown 问题
- package_info() 设置 bindirs 而非 libs
- commands.json 需要 (R38: 命令行工具)
---

**编译结束**: 2026-08-07 16:43
**最终状态**: built
