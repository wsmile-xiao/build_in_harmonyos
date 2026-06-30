# E082: OHOS 平台 POSIX clock_gettime 兼容性问题

## 错误表现

在 OHOS 平台上编译使用 POSIX timer 的库时，出现 `CLOCK_REALTIME` 或 `CLOCK_MONOTONIC` 未定义的错误：

```c
error: 'CLOCK_REALTIME' undeclared (first use in this function)
error: 'CLOCK_MONOTONIC' undeclared (first use in this function)
error: implicit declaration of function 'clock_gettime' [-Wimplicit-function-declaration]
error: storage size of 'ts' isn't known
```

## 根因分析

OHOS 平台的头文件组织方式与标准 POSIX 系统有所不同：

1. **头文件包含问题**：`<time.h>` 可能需要配合其他宏定义才能暴露 `CLOCK_*` 常量
2. **sysroot 应用问题**：交叉编译时 sysroot 可能未正确传递到预处理器
3. **平台差异**：OHOS 可能未完整实现 POSIX timer 接口

验证命令：
```bash
# 检查 SDK 中 CLOCK_* 定义
echo '#include <time.h>
#include <stdio.h>
int main() { printf("%d\n", CLOCK_REALTIME); return 0; }' > test_clock.c
clang --target=aarch64-linux-ohos --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot test_clock.c
```

## 解决方案

### 方案 1：禁用 POSIX Timer（推荐）

大多数库提供了禁用 POSIX timer 的编译选项：

**CMake 项目**：
```bash
cmake .. -DSUPPORT_POSIX_TIMERS=OFF
# 或
cmake .. -DUSE_POSIX_TIMERS=OFF
```

**Autotools 项目**：
```bash
./configure --disable-posix-timers
```

**手动修改源码**：
```c
// 在配置头文件中添加
#define SUPPORT_POSIX_TIMERS 0

// 或使用条件编译
#ifndef CLOCK_REALTIME
#define CLOCK_REALTIME 0
#endif
```

### 方案 2：使用 SDL Backend

对于图形库（如 raylib），可以使用 SDL backend，SDL 已经处理了平台兼容性问题：

```bash
# raylib 编译示例
cmake .. -DPLATFORM=SDL
```

### 方案 3：添加缺失的定义

如果必须使用 POSIX timer，可以手动添加缺失的定义：

```c
#ifndef CLOCK_REALTIME
#define CLOCK_REALTIME 0
#endif
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 4
#endif
```

但这种方法可能隐藏更深层的平台差异问题，不推荐。

## 受影响的软件

- raylib（图形库）
- SDL 相关项目
- 使用 `clock_gettime()` 的跨平台库
- 游戏引擎和多媒体库

## 案例

### raylib 6.0 编译失败

在 raylib 6.0 编译过程中，`rcore.c` 使用了 `CLOCK_REALTIME` 和 `CLOCK_MONOTONIC`：

```c
// raylib/src/rcore.c
#include <time.h>

// 编译错误
error: 'CLOCK_MONOTONIC' undeclared (first use in this function)
    clock_gettime(CLOCK_MONOTONIC, &ts);
```

**解决方法**：

**尝试 1**：手动验证成功
```bash
# 单独编译测试文件可以成功
clang -c test_clock.c --target=aarch64-linux-ohos --sysroot=...
```

**尝试 2**：使用 Make 构建失败
```bash
cd raylib/src
make PLATFORM=PLATFORM_DESKTOP
# 仍然失败，可能是 Makefile 未正确传递 sysroot
```

**推荐方案**：使用 SDL backend
```bash
cmake .. -DPLATFORM=SDL
make -j2
```

## 注意事项

1. **不要简单添加定义**：直接定义 `CLOCK_REALTIME` 可能导致运行时问题
2. **检查 sysroot 传递**：确保编译器正确接收 `--sysroot` 参数
3. **考虑替代方案**：`gettimeofday()` 在 OHOS 上更可靠

## 相关原则

- P003: 平台兼容性优先原则
- P008: 避免硬编码平台差异