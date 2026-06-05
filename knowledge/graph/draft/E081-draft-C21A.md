# E081: HarmonyOS 缺少 pthread_cancel 系列函数

## 错误模式

**典型错误日志**：
```
error: use of undeclared identifier 'pthread_cancel'
error: use of undeclared identifier 'pthread_setcanceltype'
error: use of undeclared identifier 'pthread_setcancelstate'
```

**触发条件**：
- 编译使用 pthread_cancel 系列函数的源码
- HarmonyOS 系统上编译多线程库（如 OpenMP 运行时 libomp）

## 根因分析

HarmonyOS 内核不支持 POSIX 线程取消机制，具体缺失：
- `pthread_cancel()` - 取消线程执行
- `pthread_setcanceltype()` - 设置取消类型
- `pthread_setcancelstate()` - 设置取消状态

这与 Android 系统类似，Android 也因为安全考虑不支持这些函数。

## 解决方案

### 方案 1：添加平台守卫（推荐）

在源码中添加条件编译：

```c
// 原代码可能是：
#define KMP_CANCEL_THREADS

// 修改为：
#define KMP_CANCEL_THREADS

// Android 和 HarmonyOS 不支持 pthread_cancel
#if defined(__ANDROID__) || defined(__OHOS__)
#undef KMP_CANCEL_THREADS
#endif
```

这样所有使用 pthread_cancel 的代码块都会因为 `#ifdef KMP_CANCEL_THREADS` 守卫而自动跳过。

### 方案 2：CMake 选项

如果软件支持，通过 CMake 选项禁用线程取消功能：
```bash
cmake -DENABLE_THREAD_CANCEL=OFF ...
```

## 案例

**libomp 15.0.4 编译**

修改文件：`runtime/src/kmp.h`

修改内容：
```c
// Android does not have pthread_cancel.  Undefine KMP_CANCEL_THREADS if being
// built on Android
// HarmonyOS also does not have pthread_cancel support
#if defined(__ANDROID__) || defined(__OHOS__)
#undef KMP_CANCEL_THREADS
#endif
```

## 验证

检查 HarmonyOS pthread.h 中是否包含这些函数：
```bash
grep -r "pthread_cancel\|pthread_setcancel" /path/to/sysroot/usr/include/pthread.h
```

预期结果：无匹配（函数不存在）

## 受影响软件

- libomp (OpenMP 运行时库)
- 其他使用线程取消机制的多线程库
- 某些线程调试/监控工具

## 原则引用

- **R8**: 源码"四不"准则 - 使用 `#ifdef __OHOS__` 守卫处理平台差异

---

*Draft created: 2026-05-19 by C21A (libomp-15.0.4 编译任务)*