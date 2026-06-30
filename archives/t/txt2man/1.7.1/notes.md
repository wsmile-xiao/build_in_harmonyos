# txt2man 1.7.1 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile 项目，无 configure)
- 编译日期: 2026-06-15
- 编译器: clang/clang++ (txt2man 为 shell 脚本，不需要编译器)
- 状态: built

## 编译步骤

txt2man 是一个 shell 脚本工具，将 flat ASCII text 转换为 man page 格式。
它没有 configure 脚本，使用简单 Makefile 安装。

1. 修改 Makefile 添加 DESTDIR 支持（用于 staging 安装）
2. `make prefix=$DEFAULT_PREFIX` — 使用 txt2man 自身生成 man pages
3. `make install prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` — staging 安装
4. 验证 staging 安装文件
5. `make install prefix=$DEFAULT_PREFIX` — 正式安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build URL下载失败 | SSL证书验证失败 | 手动 curl下载，使用 file:// URL |
| 2 | Makefile 不支持 DESTDIR | 原始 Makefile 没有 DESTDIR 变量 | 添加 DESTDIR ?= 并修改 install 规则 |
| 3 | G0 clean-verify 失败 | txt2man 没有 configure 脚本 | 创建 hints.yaml (skip_configure: true)，纯 Makefile 项目不需要 configure |
| 4 | manifest 缺少 build_system | init-build 默认生成 autotools | 更新为 build_system: makefile |

## 源码修改

- 0001-Makefile.patch: 添加 DESTDIR 支持用于 staging 安装隔离

## 依赖版本

- gawk 5.4.0 (用于生成 man pages)

## 验证结果

```bash
$ ls $TEST_PREFIX/$DEFAULT_PREFIX/bin/
bookman  src2man  txt2man

$ txt2man -h
NAME
  txt2man - convert flat ASCII text to man page format
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| txt2man-1.7.1-ohos-aarch64.tar.gz | 39KB | aarch64 预编译包 |
| txt2man-1.7.1-ohos-aarch64-debug.tar.gz | 2.5KB | debug 包(纯 shell 脚本无调试符号) |

## 注意事项

- txt2man 是纯 shell 脚本工具，不需要编译器
- 需要依赖 gawk 运行时用于生成 man pages
- G0 干净构建验证不适用于纯 Makefile 项目（clean-verify 总是尝试 configure）
---

**编译结束**: 2026-06-15 11:08
**最终状态**: built
