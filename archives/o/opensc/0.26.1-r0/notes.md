# opensc 0.26.1-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 构建流程

opensc GitHub release tarball 包含完整的 configure 脚本，无需 bootstrap。

1. **Configure**: `./configure --prefix=$DEFAULT_PREFIX --disable-notify --disable-static --enable-shared`
2. **Make**: `make -j1`
3. **Install**: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原有 28 个 patch 全是构建产物 | `per-file-difflib` 比对含构建产物的 work 目录 | 按 R6 铁律全部删除，0 patch |
| 2 | config.guess/sub 无需修改 | opensc tarball 的 config.guess 已支持 `linux-ohos` | 不需要 config.guess/sub patch |

## 补丁清单

无补丁。所有差异都是构建产物（Makefile/config.log/config.status/libtool/二进制），应由 configure 自动生成。

## 知识沉淀

- opensc 的 config.guess 已原生支持 HarmonyOS 平台识别为 `aarch64-unknown-linux-ohos`
- R6: 所有 autotools 生成的 Makefile/config/libtool 不应 patch，只保留源文件修改