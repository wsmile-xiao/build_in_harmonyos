# udpping 0.0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化构建环境：`ohc-run.py init-build udpping 0.0.2`
2. CMake 配置：`cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release`
3. 编译：`cmake --build build -j1`
4. Staging 安装：`DESTDIR=$TEST_PREFIX cmake --install build --prefix $DEFAULT_PREFIX`
5. 本地安装：`cmake --install build --prefix $DEFAULT_PREFIX`
6. 打包：`ohc-run.py package udpping 0.0.2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `struct timeval` 不完整类型 | OpenHarmony 缺少 `<sys/time.h>` 头文件 | 在 udpping.c 添加 `#include <sys/time.h>` |
| 2 | cmake --install 无安装规则 | CMakeLists.txt 缺少 install() 命令 | 在 CMakeLists.txt 添加 `install(TARGETS udpping DESTINATION bin)` |

## 源码修改

- **0001-add-sys-time-h.patch**: 在 udpping.c 添加 `#include <sys/time.h>` 头文件
- **0002-add-install-rule.patch**: 在 CMakeLists.txt 添加 `install(TARGETS udpping DESTINATION bin)` 安装规则

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- pthread: 系统自带

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/udpping
-s/-c must be specified
Usage: udpping [-s] [-c server] [-p port] [args]
...
```

程序可正常执行，显示使用帮助信息。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| udpping-0.0.2-ohos-aarch64.tar.gz | 81KB | 预编译包（ELF 已签名） |
| udpping-0.0.2-ohos-aarch64-debug.tar.gz | 31KB | 调试符号包 |

## 注意事项

- udpping 是 UDP ping 工具，支持服务器和客户端两种模式
- 无 --version 参数，验证时使用不带参数的命令触发帮助信息
- 链接 pthread 库，使用 UDP socket 进行网络探测
- 不需要特殊权限（与 hping 不同，不需要 raw socket）

## 知识提取

- E007 平台真理：OpenHarmony 需要 `<sys/time.h>` 才能使用 `struct timeval`（已作为补丁记录）---

**编译结束**: 2026-08-23 00:26
**最终状态**: built
---

**编译结束**: 2026-08-23 00:31
**最终状态**: published
