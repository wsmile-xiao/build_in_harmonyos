# E_musl_pthread_affinity: musl libc pthread affinity 扩展缺失

## 问题概述

在 OpenHarmony（musl libc）系统上编译使用 pthread affinity API 的软件时，会出现编译错误。

## 症状

```
error: use of undeclared identifier 'pthread_getaffinity_np'
error: use of undeclared identifier 'pthread_setaffinity_np'
error: did you mean 'sched_setaffinity'
```

## 根因分析

- musl libc 不支持 glibc 的 pthread affinity 扩展函数
- `pthread_getaffinity_np` 和 `pthread_setaffinity_np` 是 glibc 特有扩展
- OpenHarmony 使用 musl libc，缺少这些函数

## 解决方案

使用标准 POSIX 函数替代：

```c
// 原代码 (glibc)
pthread_getaffinity_np(thread, sizeof(cpu_set_t), &affinity);
pthread_setaffinity_np(thread, sizeof(cpu_set_t), &affinity);

// 替换为 (musl libc 兼容)
sched_getaffinity(0, sizeof(cpu_set_t), &affinity);  // pid=0 表示当前线程
sched_setaffinity(0, sizeof(cpu_set_t), &affinity);
```

**注意**：
- 参数从 `pthread_t` 改为 `pid_t`，值为 0 表示当前线程/进程
- 需要确保 `<sched.h>` 中定义了 `cpu_set_t`

## 受影响软件

- OpenImageDenoise
- TBB (潜在)
- OpenMPI (潜在)
- 其他使用 pthread affinity API 的软件

## 补丁示例

### OpenImageDenoise

文件: `core/thread.cpp`

```patch
--- a/core/thread.cpp
+++ b/core/thread.cpp
@@ -186,8 +186,10 @@ namespace oidn {

   void ThreadAffinity::get(ThreadAffinity& affinity)
   {
-    pthread_getaffinity_np(thread, sizeof(cpu_set_t), &affinity.set);
+    // Use sched_getaffinity for musl libc compatibility
+    sched_getaffinity(0, sizeof(cpu_set_t), &affinity.set);
   }

   void ThreadAffinity::set(const ThreadAffinity& affinity)
   {
-    pthread_setaffinity_np(thread, sizeof(cpu_set_t), &affinity.set);
+    // Use sched_setaffinity for musl libc compatibility
+    sched_setaffinity(0, sizeof(cpu_set_t), &affinity.set);
   }
```

## 参考资料

- musl libc 文档: https://musl.libc.org
- POSIX sched_getaffinity: https://pubs.opengroup.org/onlinepubs/9699919799/