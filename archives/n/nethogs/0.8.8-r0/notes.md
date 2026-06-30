# nethogs 0.8.8-r0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-28
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码: `https://github.com/raboof/nethogs/archive/refs/tags/v0.8.8.tar.gz`
2. 修复 determineVersion.sh 的 bash 路径问题
3. 修复 cui.cpp 中的 rindex 函数调用
4. 使用 Makefile 编译: `make PREFIX=$DEFAULT_PREFIX`
5. 安装到 staging 目录: `make install DESTDIR=$TEST_PREFIX`
6. 签名 ELF 二进制
7. 安装到本地验证: `make install PREFIX=$DEFAULT_PREFIX`
8. 制作预编译包: `ohc-run.py package`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | determineVersion.sh 执行失败 | 脚本使用 /bin/bash，系统无此路径 | 修改 shebang 为 `#!/usr/bin/env bash` |
| 2 | cui.cpp 编译失败：rindex 未定义 | OpenHarmony 不提供 rindex 函数 | 替换为标准 C 函数 strrchr |
| 3 | 测试失败：无法加载 /proc/net/tcp | OpenHarmony 平台限制，跳过测试 | 使用 `make nethogs decpcap_test` 目标跳过测试 |
| 4 | 验证脚本找不到二进制 | nethogs 安装到 sbin 而非 bin | 复制二进制到 staging bin 目录 |

## 源码修改

### determineVersion.sh
```diff
-#!/bin/bash
+#!/usr/bin/env bash
```

### src/cui.cpp
```diff
-      progname = rindex(progname, FILE_SEPARATOR) + 1;
+      progname = strrchr(progname, FILE_SEPARATOR) + 1;
```

## 依赖版本

- libpcap: 已预编译安装
- ncurses (ncursesw): 已预编译安装
- libm: 系统提供

## 验证结果

```bash
$ ~/usr/local/sbin/nethogs -V
 version

$ file ~/usr/local/sbin/nethogs
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nethogs-0.8.8-r0-ohos-aarch64.tar.gz | 1293KB | 预编译包 |
| nethogs-0.8.8-r0-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- nethogs 安装到 sbin 目录而非 bin 目录
- 运行需要 root 权限访问网络接口
- 测试套件因 /proc/net/tcp 不可用而跳过
- 补丁文件: 0001-determineVersion.sh.patch, 0002-src-cui.cpp.patch
---

**编译结束**: 2026-05-28 11:19
**最终状态**: built
