# libomemo 0.8.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-11
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 初始化编译环境：`python3 scripts/ohc-run.py init-build libomemo 0.8.1 --url=https://codeload.github.com/gkdr/libomemo/tar.gz/refs/tags/v0.8.1`
2. 创建 Mini-XML v4 API 兼容层：`src/mxml4_compat.h`
3. 修改源码引用兼容头文件：`src/libomemo.c`
4. CMake 配置：`cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DOMEMO_WITH_TESTS=OFF -DBUILD_SHARED_LIBS=OFF ..`
5. 编译：`make -j1`
6. 安装到 staging：`make install DESTDIR=$TEST_PREFIX`
7. 验证：`python3 scripts/ohc-run.py verify-build libomemo 0.8.1`
8. 打包：`python3 scripts/ohc-run.py package libomemo 0.8.1`
9. 本地安装：`make install`
10. 完成：`python3 scripts/ohc-run.py finish libomemo 0.8.1 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Mini-XML API 不兼容 | libomemo 0.8.1 使用 Mini-XML v2/v3 API（MXML_NO_PARENT, MXML_OPAQUE_CALLBACK 等），但本地安装的是 mxml4 v4.0.4，API 有破坏性变更 | 创建 `mxml4_compat.h` 兼容层，提供 wrapper 函数和宏定义适配新旧 API |

## 源码修改

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/mxml4_compat.h` | 新增 | Mini-XML v4 API 兼容层，包含 wrapper 函数和宏映射 |
| `src/libomemo.c` | 修改 | 添加 `#include "mxml4_compat.h"` 引用兼容层 |

## 依赖版本

| 依赖 | 版本 | pkg-config 名称 |
|------|------|-----------------|
| glib | 2.88.0 | glib-2.0 |
| libgcrypt | 1.11.0 | libgcrypt |
| mxml | 4.0.4 | mxml4 (通过 mxml.pc 兼容层映射) |
| sqlite3 | 3.49.1 | sqlite3 |

## 验证结果

```bash
$ pkg-config --exists libomemo && pkg-config --modversion libomemo
0.8.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libomemo-0.8.1-ohos-aarch64.tar.gz` | 83KB | 预编译包（静态库） |
| `libomemo.a` | 48KB | 静态库文件 |
| `libomemo.pc` | - | pkg-config 文件 |

## 注意事项

1. Mini-XML v4 API 与 v2/v3 有破坏性变更，需要兼容层
2. 本项目为静态库（BUILD_SHARED_LIBS=OFF），无动态库产物
3. 需要创建 `mxml.pc` 兼容层映射 `mxml4.pc`，因为 libomemo 查找 "mxml" 包名
---
**编译结束**: 2026-06-11 10:58
**最终状态**: built