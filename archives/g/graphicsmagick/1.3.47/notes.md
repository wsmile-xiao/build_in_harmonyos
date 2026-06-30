# GraphicsMagick 1.3.47 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4/clang++
- 状态: built

## 编译步骤
1. init-build下载源码（SourceForge）
2. 修改config.guess/config.sub添加HarmonyOS检测
3. 修改configure中umask 077→022（HMDFS权限修复）
4. bash ./configure --prefix=$DEFAULT_PREFIX --enable-static --disable-shared
5. make -j1 && make install DESTDIR=$TEST_PREFIX
6. package生成预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub不识别HarmonyOS | GNU config无ohos检测 | 添加HarmonyOS分支 |
| 2 | configure中umask 077导致临时目录权限错误 | HMDFS文件系统限制 | umask 077→022 |
| 3 | ECHO='print -r --'导致libtool失败 | toybox sh检测了print作为ECHO | 使用bash代替/bin/sh |
| 4 | PerlMagick Makefile.PL路径问题 | perl路径检测 | 修改Makefile.PL |

## 补丁文件
- 0001-PerlMagick-Makefile.PL.patch: Perl路径修复
- 0002-config-config.guess.patch: HarmonyOS检测
- 0003-config-config.sub.patch: ohos-linux triplet
- 0004-configure.patch: umask 077→022修复

## 验证结果
```bash
$ gm version
GraphicsMagick 1.3.47 2026-05-13 Q8
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| graphicsmagick-1.3.47-ohos-aarch64.tar.gz | 20M | Release制品 |
| graphicsmagick-1.3.47-ohos-aarch64-debug.tar.gz | 696K | Debug符号包 |
