# async_simple

alibaba 开源的 C++20 异步组件库，提供基于协程（coroutine）和用户态线程（uthread）的高性能异步编程框架。

## 特性

- **C++20 协程支持**: Lazy/Generator/Semaphore/Mutex 等协程原语
- **uthread 用户态线程**: 基于 aarch64 汇编的上下文切换，提供类线程的异步编程模型
- **Future/Promise**: 异步计算和值传递
- **Executor**: 可定制的执行器（SimpleExecutor/SimpleIOExecutor）
- **Header-only 选项**: 无 uthread 时为纯头文件库

## 编译版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.4 | published | 2026-06-17 |

## 依赖

- pthread（系统内置）
- C++20 编译器（clang++ 15+ / gcc 11+）

## 使用方式

```cmake
find_package(async_simple REQUIRED)
target_link_libraries(myapp async_simple::async_simple)
```

或仅使用头文件版：

```cmake
find_package(async_simple REQUIRED)
target_link_libraries(myapp async_simple::async_simple_header_only)
```

## 注意事项

- OHOS 上需设置 `CMAKE_SYSTEM_NAME=Linux` 以启用 uthread 组件
- AIO 默认禁用（`ASYNC_SIMPLE_DISABLE_AIO=ON`），因为 OHOS 不支持 libaio
- 编译时需确保 `-std=c++20` 和 C++20 协程支持
