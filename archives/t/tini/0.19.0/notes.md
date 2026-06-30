# tini 0.19.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码包 tini-0.19.0.tar.gz
2. 解压到 ~/tmp/builds/tini-0.19.0.work
3. 修复 CMakeLists.txt 中 cmake_minimum_required 版本 (2.8.0 → 3.5)
4. 修复 src/tini.c 中函数原型声明 (添加 void 参数)
5. 运行 cmake 配置: `cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release ..`
6. 运行 make 编译
7. 运行 make install DESTDIR=... 安装到 staging 目录
8. 打包预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本兼容性错误 | cmake_minimum_required(VERSION 2.8.0) 过低 | 更改为 cmake_minimum_required(VERSION 3.5) |
| 2 | 函数原型警告变为错误 | Clang 严格检查旧式 C 函数定义 | 添加 void 参数: `int func()` → `int func(void)` |

## 源码修改

- CMakeLists.txt: cmake_minimum_required 版本升级
- src/tini.c: 修复 4 个函数的原型声明 (isolate_child, parse_env, register_subreaper, reaper_check)

## 依赖版本

无外部依赖，纯 C 项目

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/tini --version
tini version 0.19.0
$ /storage/Users/currentUser/usr/local/bin/tini-static --version
tini version 0.19.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tini-0.19.0-ohos-aarch64.tar.gz | 322KB | 预编译包 |
| tini-0.19.0-ohos-aarch64-debug.tar.gz | 37KB | 调试符号包 |

## 注意事项

- tini 没有 make check 测试套件
- 需要应用 2 个补丁才能在新版 CMake 和 Clang 下编译
- 知识图谱已有相关条目 E103 (cmake 版本兼容性)
---

**编译结束**: 2026-05-27 20:46
**最终状态**: published
