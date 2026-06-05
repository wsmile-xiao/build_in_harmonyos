# E094: musl libc POSIX 定时器常量未定义

## 错误表现

编译时报错：
```
error: use of undeclared identifier 'CLOCK_REALTIME'
error: use of undeclared identifier 'CLOCK_MONOTONIC'
warning: call to undeclared function 'clock_gettime'
```

## 根因分析

musl libc 与 glibc 的行为差异：
- **glibc**: 自动定义 POSIX 定时器常量和函数，即使没有显式包含 time.h
- **musl**: 更严格，需要显式 `#include <time.h>`，有时还需要 `_GNU_SOURCE` 宏

HarmonyOS/musl 中：
- `CLOCK_REALTIME = 0`
- `CLOCK_MONOTONIC = 1`
- 这些定义存在于 time.h，但需要正确包含

## 影响范围

使用 POSIX 定时器 API 的软件：
- 图形库：glfw, sdl, opengl 相关
- 定时器应用：需要高精度定时、帧率控制
- 系统监控：需要测量时间间隔

## 解决方案

### 方案 1（推荐）：源码补丁

1. 添加 `#include <time.h>` 到相关源文件
2. 配置编译器标志：
   - CMake: `-DCMAKE_C_FLAGS="-D_GNU_SOURCE"`
   - Autotools: `CFLAGS="-D_GNU_SOURCE"`

### 方案 2（回退）：手动修复

如果源文件已包含 time.h 但仍报错：
- 添加 `_POSIX_C_SOURCE=200809L` 到编译器标志
- 检查是否有其他头文件冲突

## 示例案例

### glfw 3.4

**问题**：编译 posix_time.c 时 CLOCK_REALTIME 未定义

**解决**：
```c
// src/posix_time.c
#include "internal.h"

#if defined(GLFW_BUILD_POSIX_TIMER)

#include <unistd.h>
#include <sys/time.h>
#include <time.h>  // 新增
```

**编译命令**：
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_FLAGS="-D_GNU_SOURCE"
make -j2
```

## 验证命令

```bash
# 检查是否包含 time.h
grep -n "time.h" src/posix_time.c

# 检查编译器标志
grep "GNU_SOURCE" CMakeLists.txt || grep "GNU_SOURCE" configure.ac

# 验证编译成功
make clean && make -j2
```

## 禁止做法

无特殊禁止项。正常添加头文件和编译器标志即可。

## 关联条目

- E020: musl FILE 不透明类型
- 相似问题：musl libc 与 glibc 行为差异

## 原则引用

- **R6**: 只改源文件不改生成文件
- **R15**: 历史仅供参考，实际参数以本次编译为准