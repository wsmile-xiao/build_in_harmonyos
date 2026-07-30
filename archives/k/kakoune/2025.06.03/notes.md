# kakoune 2025.06.03 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

kakoune 使用纯 Makefile 构建，无需 configure 步骤：

```bash
# 编译（直接在源码根目录执行 make）
make -j2

# 安装到临时目录
make install DESTDIR=./install PREFIX=/usr/local
```

编译产物为 `src/kak` 可执行文件，安装后位于 `install/usr/local/bin/kak`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 编译报错 `'rename' was not declared` | OHOS 工具链部分系统头文件包含链不完整，缺少 `<stdio.h>` 隐式声明 | 添加补丁 `0001-add-stdio-h.patch`，在 `src/buffer_utils.cc` 中显式 `#include <stdio.h>` |

## 源码修改

- `0001-add-stdio-h.patch`: `src/buffer_utils.cc` 添加 `#include <stdio.h>`，修复 OHOS 平台 `rename` 函数未声明问题

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| clang/clang++ | OHOS 工具链内置 | C++17 编译器 |
| make | 系统自带 | 构建工具 |

## 验证结果

```bash
# 验证 kak 二进制存在且可执行
./install/usr/local/bin/kak -version
# 验证运行时依赖库
ldd ./install/usr/local/bin/kak
```

test_package 验证：`conan create` 自动运行 `kak -version` 确认二进制可执行。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/kak` | kakoune 主程序可执行文件 |
| `share/kak/*.rc` | kakoune 运行时配置文件 |
| `share/kak/*.kak` | kakoune 脚本文件 |

## 注意事项

- kakoune 为 C++17 项目，需使用支持 C++17 的编译器
- 无需任何外部依赖库，纯 C++ 标准库实现
- OHOS 平台需要补丁修复 `<stdio.h>` 包含问题
