# intrusive-shared-ptr

## 一句话

intrusive-shared-ptr 是一个 C++17 header-only 库，提供可配置的侵入式共享指针、
原子访问、弱引用、引用计数基类以及面向 COM、Apple CoreFoundation 和 Python
对象的适配器。

## 功能概述

- `intrusive_shared_ptr<T, Traits>` 使用显式 `ref`/`noref` 工厂管理所有权边界
- `ref_counted`、`ref_counted_adapter` 和 `ref_counted_wrapper` 提供引用计数实现
- `weak_ref_counted` 提供弱引用与安全的强引用恢复
- `std::atomic<intrusive_shared_ptr<...>>` 特化提供原子 load/store/exchange
- 支持 C++17 头文件接口和实验性 C++20 模块源

## OHOS 适配

- 公开接口为纯头文件，无平台相关运行库依赖
- 使用 OHOS AArch64 Clang 15 同时编译并运行上游 C++17、C++20 测试变体
- Conan 包导出 `isptr::isptr` CMake 目标和 `isptr` pkg-config 名称
- 消费者测试覆盖引用计数、复制、弱引用和 OHOS 原子智能指针语义

## 依赖关系

- 编译与运行依赖：无
- 测试依赖：`doctest/2.4.11`

## 参考资料

- 源码仓库：https://github.com/gershnik/intrusive_shared_ptr
- 上游文档：https://github.com/gershnik/intrusive_shared_ptr/tree/v1.6/doc
