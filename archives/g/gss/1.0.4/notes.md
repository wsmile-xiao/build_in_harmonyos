# gss 1.0.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built（编译成功，clean-verify 未通过）

## 编译步骤

1. 初始化：`ohc-run.py init-build gss 1.0.4 --url=https://ftp.gnu.org/gnu/gss/gss-1.0.4.tar.gz`
2. 修复 config.guess/config.sub：从已编译成功的软件复制
3. 修复 configure umask：`sed -i 's/umask 077/umask 022/g' configure`
4. 修复 gnulib stdint.in.h 占位符问题
5. 修复 configure bashism：添加 bash 检测和重新执行逻辑
6. 编译：`./configure --prefix=$DEFAULT_PREFIX && make -j1`
7. 安装：`make install DESTDIR=$TEST_PREFIX`
8. 测试：`make check`（全部通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 OpenHarmony | 缺少平台标识 | 从已编译成功的软件复制更新的 config.guess/config.sub |
| 2 | configure 无法创建临时文件 | HMDFS hmmac 强制访问控制 + umask 077 | 修改 configure 中的 umask 为 022 |
| 3 | stdint.in.h 编译错误 | gnulib 占位符 `@GNULIBHEADERS_OVERRIDE_WINT_T@` 未替换 | 修改为 `#if 0` |
| 4 | stdint.h 生成失败 | 占位符 `@HAVE_C99_STDINT_H@` 未替换 | 修改为 `#if 0` |
| 5 | clean-verify 失败 | configure 包含 bashism `eval ac_cr=\$'\\r'` | 替换为 POSIX 兼容的 `ac_cr=$(printf '\r')`，添加 bash 检测 |
| 6 | clean-verify 仍失败 | toybox sh 在解析时就遇到 bashism | 添加 exec /bin/bash 重执行逻辑（仍未完全解决） |

## 源码修改

应用 5 个补丁：
- 0001-build-aux-config.guess.patch：更新平台识别
- 0002-build-aux-config.sub.patch：更新平台识别
- 0003-configure.patch：修复 umask + bashism + bash 检测
- 0006-lib-gl-stdint.in.h.patch：修复空 #if 占位符
- 0008-src-gl-stdint.in.h.patch：修复空 #if 占位符

## 依赖版本

- gettext (libintl)
- 无其他强依赖

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/gss --version
gss (GNU Generic Security Service) 1.0.4
Copyright (C) 2022 Simon Josefsson.

make check: PASS (3 tests)
```

## 交付物

暂无预编译包（clean-verify 未通过，无法发布）

## 注意事项

⚠️ **clean-verify 阻塞问题**：autoconf 生成的 configure 脚本包含大量 bashism，toybox sh 无法完全兼容。即使添加了 bash 检测逻辑，clean-verify 强制使用 `/bin/sh ./configure`（脚本硬编码），导致脚本解析时就遇到语法错误。

**解决方案建议**：
1. 修改 clean_verify.py 脚本，使其使用 bash 而不是 sh
2. 或者使用完全 POSIX 兼容的 autoconf 生成 configure

## 知识提取

新发现的错误模式：
- **E-N**: gnulib stdint.in.h 占位符未替换导致空 #if 指令
  - 症状：编译错误 `error: expected value in expression` 在 `#if` 行
  - 根因：autoconf 配置时某些变量未定义（如 GNULIBHEADERS_OVERRIDE_WINT_T）
  - 解决：修改模板文件，将 `#if @VAR@` 替换为 `#if 0`
---

**编译结束**: 2026-06-05 11:02
**最终状态**: built
