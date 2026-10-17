# unzip 6.0 编译笔记

## 编译日期
2026-05-20

## 编译环境
- 编译器: clang 15.0.4
- 目标平台: aarch64-unknown-linux-ohos
- 构建系统: unix/Makefile

## 编译过程

### 1. 源码获取
从 Debian snapshot 下载 unzip_6.0.orig.tar.gz

### 2. 配置
使用 `make -f unix/Makefile generic CC=clang`
- configure 脚本自动检测系统特性
- 启用了 Large File Support
- 启用了 UTF-8 Native 支持
- bzip2 支持未启用（缺少 bzip2 源码）

### 3. 编译
成功编译，有警告（旧式 C 函数声明）

### 4. 安装
手动安装（HMDFS 不支持硬链接）
- 复制二进制文件到 bin 目录
- 复制文档文件到 man 目录

## 遇到的问题

### HMDFS 硬链接限制
HMDFS 文件系统不支持硬链接（`ln` 命令失败）。
解决方案：使用 `cp` 复制文件代替硬链接。

### configure 脚本使用 cc
configure 脚本默认使用 `cc`，但系统中只有 `clang`。
解决方案：通过 `CC=clang` 参数指定编译器。

### linux 目标不适用于 ARM
`linux` 目标需要 Intel 汇编代码。
解决方案：使用 `generic` 目标（无汇编）。

## 产物
- unzip: 主解压工具
- funzip: 流式解压工具
- unzipsfx: 自解压模块
- zipinfo: ZIP 信息查看工具
- zipgrep: ZIP 文件搜索脚本
---

**编译结束**: 2026-07-15 18:27
**最终状态**: built
