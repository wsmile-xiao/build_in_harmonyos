# apitrace 14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载 apitrace 14.0 源码
2. 使用 CMake 构建：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
   make -j2
   make install DESTDIR=$HOME/tmp/test-install-apitrace-14.0
   ```
3. 预编译包制作：ohc package apitrace 14.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| apitrace-14.0-ohos-aarch64.tar.gz | 3.6MB | 预编译包（工具+库+脚本） |
| apitrace-14.0-ohos-aarch64-debug.tar.gz | 471KB | 调试符号包 |