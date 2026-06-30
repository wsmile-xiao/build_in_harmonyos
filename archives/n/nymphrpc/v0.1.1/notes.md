# nymphrpc v0.1.1 适配笔记

## 编译环境
- 构建系统: Makefile（非 autotools/cmake）
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: **built**（编译成功）

## 编译步骤

1. 初始化编译环境（ohc-run.py init-build）
2. 修改 Makefile：
   - 添加 POCO 头文件包含路径：`-I $(HOME)/usr/local/include`
   - 升级 C++ 标准从 c++14 到 c++17
   - 添加 `-include` 预包含修复头文件
   - 添加 libc++ 头文件路径
3. 编译依赖：POCO 1.15.3（成功）
4. 编译 NymphRPC（成功）

## 解决的关键问题

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `nullptr_t` 未定义 | HarmonyOS SDK libc++ bug + musl stddef.h 缺失 | 创建 ohos_fix.h 预包含头，定义 `__OHOS_FAMILY__` 和 `nullptr_t` |
| 2 | `__promote` 未声明 | libc++ `<cmath>` 缺少 `__type_traits/promote.h` 包含 | 在 ohos_fix.h 中包含 `__type_traits/promote.h` |
| 3 | `pthread_cond_clockwait` 未声明 | `~/usr/local/include/pthread.h` (musl) 覆盖 SDK 版本 | 移除干扰的 musl 头文件 |
| 4 | `isinf`/`isnan` 宏冲突 | `~/usr/local/include/math.h` (musl) 定义宏与 `std::isinf` 冲突 | 移除干扰的 musl 头文件 |
| 5 | 缺少 POCO 头文件路径 | Makefile 只设置 `-I src` | 添加 `-I $(HOME)/usr/local/include` |
| 6 | C++14 标准库不兼容 | HarmonyOS SDK libc++ 需要 C++17 | 升级到 `-std=c++17` |

## 创建的修复头文件

`~/usr/local/include/preinclude/ohos_fix.h`：

```cpp
// OHOS SDK libc++ fixes - must be included with -include option

#ifndef _OHOS_SDK_FIX_H
#define _OHOS_SDK_FIX_H

// Fix 1: Define OHOS platform macros
#ifndef __OHOS_FAMILY__
#define __OHOS_FAMILY__ 1
#endif

// Fix 2: Define nullptr_t in global namespace
#if defined(__cplusplus) && !defined(_LIBCPP_NULLPTR_T_IN_GLOBAL_NAMESPACE)
#define _LIBCPP_NULLPTR_T_IN_GLOBAL_NAMESPACE
typedef decltype(nullptr) nullptr_t;
#endif

#endif

// Fix 3: Include __promote template (cmath uses it without including)
#if defined(__cplusplus)
#include <__type_traits/promote.h>
#endif
```

## 编译命令

```bash
make CXX=clang++ \
    CXXFLAGS="-I src -I ~/usr/local/include -g3 -std=c++17 -O0 \
    -include ~/usr/local/include/preinclude/ohos_fix.h \
    -I /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1"
```

## 编译产物

- `libnymphrpc.a` (6.5 MB) - 静态库
- `libnymphrpc.so.0.1` (2.9 MB) - 共享库

## 安装位置

- 头文件：`~/usr/local/include/nymphrpc/*.h` (16 个)
- 静态库：`~/usr/local/lib/libnymphrpc.a`
- 共享库：`~/usr/local/lib/libnymphrpc.so.0.1`

## 源码修改记录

| 文件 | 行号 | 修改内容 | 原因 |
|------|------|---------|------|
| Makefile | 104 | `INCLUDE = -I src -I $(HOME)/usr/local/include` | 添加 POCO 头文件路径 |
| Makefile | 117 | `-include $(HOME)/usr/local/include/preinclude/ohos_fix.h` | OHOS SDK 修复 |
| Makefile | 117 | `-I ...libcxx-ohos/include/c++/v1` | libc++ 头文件路径 |

## 注意事项

1. 必须使用 `-include ohos_fix.h` 预包含修复头文件
2. 必须移除 `~/usr/local/include/` 中的 musl 头文件（math.h, pthread.h, endian.h, stddef.h 等）
3. 需要先安装 POCO 1.15.3 依赖
---

**编译结束**: 2026-06-09 14:53
**最终状态**: built
