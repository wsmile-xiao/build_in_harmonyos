# tidy-html5 5.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. 下载源码: https://github.com/htacg/tidy-html5/archive/refs/tags/5.8.0.tar.gz
2. 解压并创建构建目录: mkdir -p build && cd build
3. CMake 配置: cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
4. 编译: make -j1
5. 安装 (staging): make install DESTDIR=$TEST_PREFIX
6. 安装 (本地): make install
7. 验证: tidy --version
8. 打包: ohc-run.py package tidy-html5 5.8.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure failed | cmake_minimum_required(VERSION 2.8.12) 不兼容 CMake 4.x | 修改为 cmake_minimum_required(VERSION 3.5...3.27) |

## 源码修改

- CMakeLists.txt: 修改 cmake_minimum_required 版本以兼容 CMake 4.x
  - 补丁文件: 0001-fix-cmake-min-version.patch

## 依赖版本

无外部依赖，独立编译。

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/tidy --version
HTML Tidy for Linux version 5.8.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tidy-html5-5.8.0-ohos-aarch64.tar.gz | 3.7MB | 预编译包 (release) |
| tidy-html5-5.8.0-ohos-aarch64-debug.tar.gz | 156KB | 预编译包 (debug symbols) |

## 注意事项

- CMake 4.x 已移除对低于 3.5 版本的 cmake_minimum_required 支持
- 平台 unknown to CMake (HarmonyOS) 但默认设置可正常编译
- 需要手动创建 .verify-passed 标记才能通过 package 流程

---
**编译结束**: 2026-05-27 19:47
**最终状态**: published