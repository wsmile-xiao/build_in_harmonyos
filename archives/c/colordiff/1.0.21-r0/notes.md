# colordiff 1.0.21-r0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Perl 脚本，无 configure）
- 编译日期: 2026-05-20
- 编译器: 无需编译（Perl 脚本）
- Perl 版本: v5.42.2 (harmonybrew)
- 状态: built

## 编译步骤

colordiff 是纯 Perl 脚本，无需 configure 和编译步骤：

```bash
# 1. 初始化编译环境
python3 $SKILL_ROOT/scripts/ohc-run.py init-build colordiff 1.0.21-r0 --url=https://www.colordiff.org/colordiff-1.0.21.tar.gz

# 2. 直接安装到 staging 目录
cd $BUILD_SRC_DIR
make install DESTDIR=$TEST_PREFIX INSTALL_DIR=$DEFAULT_PREFIX/bin MAN_DIR=$DEFAULT_PREFIX/share/man/man1 ETC_DIR=$DEFAULT_PREFIX/etc

# 3. 验证和打包
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build colordiff 1.0.21-r0
python3 $SKILL_ROOT/scripts/ohc-run.py package colordiff 1.0.21-r0

# 4. 本地安装验证
make install INSTALL_DIR=$DEFAULT_PREFIX/bin MAN_DIR=$DEFAULT_PREFIX/share/man/man1 ETC_DIR=$DEFAULT_PREFIX/etc
colordiff --version
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Perl shebang `/usr/bin/perl` 不存在 | HarmonyOS Perl 安装在 harmonybrew 目录 | 修改 shebang 为 `#!/usr/bin/env perl`，增加可移植性 |
| 2 | Savannah 下载源 404 | Savannah 上无 colordiff 目录 | 使用官网 www.colordiff.org 下载 |
| 3 | manifest 缺少 build_system 字段 | 验证脚本检查的字段名不同 | 添加顶层 build_system: makefile 字段 |

## 源码修改

### 0001-colordiff.pl.patch

修改 Perl shebang 以增加跨平台可移植性：

```diff
--- a/colordiff.pl
+++ b/colordiff.pl
-#!/usr/bin/perl
+#!/usr/bin/env perl
```

**修改原因**: HarmonyOS 的 Perl 安装在 `~/.harmonybrew/bin/perl`，使用 `#!/usr/bin/env perl` 可自动定位 Perl 解释器。

## 依赖版本

- Perl: v5.42.2 (harmonybrew)
- diffutils: 3.12 (colordiff 的运行依赖)
- 无编译依赖

## 验证结果

```bash
$ colordiff --version
diff (GNU diffutils) 3.12
# colordiff 是 diff 的包装脚本，显示 diff 版本表示运行正常
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| colordiff-1.0.21-r0-ohos-aarch64.tar.gz | 9KB | 预编译包（含 colordiff、cdiff、手册页、配置文件） |

## 注意事项

1. colordiff 是纯 Perl 脚本，无需编译，只需安装
2. 需要 Perl 和 diffutils 作为运行依赖
3. 配置文件 colordiffrc 安装到 `$PREFIX/etc/colordiffrc`，用户可复制到 `~/.colordiffrc` 自定义颜色方案
4. 默认配置适合深色背景，浅色背景用户应使用 colordiffrc-lightbg
---

**编译结束**: 2026-08-06 04:27
**最终状态**: built
