# eventpp

eventpp 是一个 C++ 事件库，提供回调列表（CallbackList）、事件分发器（EventDispatcher）和事件队列（EventQueue）三大核心组件，可用于实现信号/槽机制、发布/订阅模式和观察者模式。

## 功能概述
- CallbackList：可追加、插入、移除回调的有序列表，支持嵌套事件和线程安全
- EventDispatcher：基于事件类型的分发器，支持多监听器
- EventQueue：异步事件队列，支持 enqueue/process 模式
- 线程安全（基于 std::mutex/std::atomic）
- 异常安全（强异常保证）
- Header-only，仅需 C++11，零外部依赖
- Apache 2.0 许可证

## OHOS 适配
- Header-only 库（CMake INTERFACE 目标），无需编译库文件
- 纯 C++11 标准库实现，零外部依赖，鸿蒙原生兼容
- 需设置 `CMAKE_SYSTEM_NAME=Linux`（OHOS 平台适配，E092）
- 线程同步基于 `std::mutex`/`std::atomic`/`std::condition_variable`，鸿蒙运行时完整支持
- 无需任何源码补丁

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/wqking/eventpp
- 文档: https://github.com/wqking/eventpp/blob/master/doc/introduction.md
