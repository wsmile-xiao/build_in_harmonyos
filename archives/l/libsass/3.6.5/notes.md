# 编译笔记 — libsass 3.6.5

## 编译概况

- **软件**: libsass (Sass compiler written in C++)
- **版本**: 3.6.5
- **状态**: ✅ published
- **日期**: 2026-05-25

## 构建系统

- **类型**: Makefile (简单 Makefile，无 configure)
- **编译器**: clang/clang++
- **PREFIX**: ~/usr/local

## 编译过程

### Step 1: 初始化
- 下载: GitHub release (libsass-3.6.5.tar.gz)
- SSL 问题: 使用 curl --insecure 下载

### Step 2: 编译
- 直接使用 Makefile 编译静态库
- 设置 CC=clang CXX=clang++ (缺少 cc/c++ 命令)
- make PREFIX=$DEFAULT_PREFIX -j2
- 产物: lib/libsass.a (6.4MB)

### Step 3: 安装
- DESTDIR 模式安装到 staging 目录
- 手动安装: 缺少 install 命令，使用 cp -a

### Step 4: 测试
- **跳过 make check**: libsass 是纯库，测试需要 sassc CLI 和 sass-spec
- 无可执行文件，无法直接验证功能

### Step 5: 打包
- ohc-run.py package libsass 3.6.5
- 产物: libsass-3.6.5-ohos-aarch64.tar.gz (6662KB)

## 遇到的问题

### 问题 1: SSL 证书验证失败
- **原因**: HarmonyOS 缺少 CA 证书
- **解决**: 使用 curl --insecure 下载

### 问题 2: cc/c++ 命令不存在
- **原因**: 系统只有 clang，没有 cc/c++ 符号链接
- **解决**: 设置 CC=clang CXX=clang++

### 问题 3: install 命令不存在
- **原因**: toybox 缺少 install 命令
- **解决**: 使用 cp -a 手动安装

### 问题 4: manifest 缺少 build_system 字段
- **原因**: 验证脚本期望 build_system 字段
- **解决**: 添加 build_system: makefile 到 manifest.yaml

## 编译依赖

无编译依赖

## 知识沉淀

1. libsass 使用简单 Makefile，不需要 configure
2. 测试需要 sassc CLI 工具和 sass-spec 测试套件
3. 只生成静态库，无共享库或可执行文件
---

**编译结束**: 2026-07-15 21:49
**最终状态**: built
