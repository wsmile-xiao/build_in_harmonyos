# E080: musl libc pthread_cancel 缺失

**分类**: 平台限制 (L1 平台真理)
**严重性**: 🔴 阻塞
**影响软件**: squashfs-tools, 其他使用线程取消功能的软件

## 问题现象

链接阶段出现错误：
```
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by restore.c
ld.lld: error: undefined symbol: pthread_testcancel
>>> referenced by mksquashfs.c
```

## 根因分析

HarmonyOS 使用 musl libc 作为 C 标准库实现。musl libc 是轻量级实现，不完全支持 POSIX 线程取消 API：
- `pthread_cancel` - 取消线程执行
- `pthread_testcancel` - 测试取消点

这些函数在 musl 中没有实现，导致链接失败。

## 适用场景

- HarmonyOS / OpenHarmony 系统
- 使用 musl libc 的嵌入式 Linux 系统
- 源码使用 `pthread_cancel` 或 `pthread_testcancel` 的软件

## 解决方案

### 方案 1: 创建存根函数（推荐）

创建 `pthread_compat.c` 提供空实现：

```c
#include <pthread.h>

int pthread_cancel(pthread_t thread) {
    (void)thread;
    return 0;  // 返回成功但不执行实际操作
}

void pthread_testcancel(void) {
    // 空操作
}
```

编译时包含此文件：
```bash
clang -c pthread_compat.c
clang ... pthread_compat.o -lpthread -lm -lz -o mksquashfs
```

**优点**: 快速解决，不修改原有源码
**限制**: 线程取消功能失效（影响异常终止场景）

### 方案 2: 修改源码

移除源码中的线程取消调用（需要理解代码逻辑）

## 验证方法

```bash
# 检查系统 libc 中是否有这些函数
nm -D /system/lib/llvm/libc.so | grep pthread_cancel
# 输出空表示不存在

# 检查 musl 是否支持
find /system -name "*pthread*" -o -name "*musl*"
```

## 注意事项

- 线程取消主要用于异常终止场景，正常使用影响较小
- 存根函数返回 0（成功）但不执行实际取消操作
- 对于 squashfs-tools，存根方案已验证可用

## 相关原则

- **R23**: 平台检测机制优先于修改生成文件

## 知识层级

L1 平台真理 - 所有使用线程取消的软件都可能遇到此问题