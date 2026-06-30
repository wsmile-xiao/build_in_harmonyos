# xplanet 1.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化构建环境：`ohc-run.py init-build xplanet 1.3.0 --url=https://downloads.sourceforge.net/project/xplanet/xplanet/1.3.0/xplanet-1.3.0.tar.gz`
2. 应用 config.guess/config.sub 修复（平台识别）
3. 修改 configure 使用 umask 002（绕过 HMDFS 权限限制）
4. 修复 C++11 兼容性问题（getline 返回值比较、narrowing 转换）
5. 运行 configure：`./configure --prefix=$DEFAULT_PREFIX`
6. 运行 make：`make -j2`
7. 运行 make install DESTDIR=$TEST_PREFIX（staging）
8. 验证：`xplanet --version`
9. 创建预编译包：`ohc-run.py package`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧版 config.guess（2003年）不支持新平台 | 替换为 automake-1.16 提供的最新版本 |
| 2 | configure 临时目录权限错误 | umask 077 创建的目录 UID 不匹配 | 修改 configure 使用 umask 002 |
| 3 | C++ getline 返回值比较错误 | C++11+ 中 getline 返回 istream& 而非指针 | 移除 != NULL 比较，使用流的 bool 转换 |
| 4 | C++ narrowing 转换错误 | 初始化列表中 int 到 unsigned char 缩窄 | 添加显式类型转换 |

## 源码修改

共 10 个文件修改：
- config.guess: 平台检测更新
- config.sub: 平台检测更新
- configure: umask 002 修复
- src/libannotate/*.cpp: getline 比较修复（4个文件）
- src/libmultiple/*.cpp: getline 比较（2个文件）
- src/readConfig.cpp: getline + narrowing 修复

## 依赖版本

无外部依赖（使用内置库）

## 验证结果

```bash
$ xplanet --version
Xplanet 1.3.0
Copyright (C) 2012 Hari Nair <hari@alumni.caltech.edu>
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| xplanet-1.3.0-ohos-aarch64.tar.gz | 2350KB | 预编译包 |
| xplanet-1.3.0-ohos-aarch64-debug.tar.gz | 4720KB | 调试符号包 |

## 注意事项

- umask 002 修复是 HMDFS 文件系统的特殊 workaround，未来平台更新可能不再需要
- 无 X11/freetype 等图形支持（符合预期，无显示环境）
---

**编译结束**: 2026-06-11 17:46
**最终状态**: built
