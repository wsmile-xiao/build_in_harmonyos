# atomic_queue

C++ 高性能 lock-free 并发队列库，由 Maxim Egorushkin 开发。本仓库提供其在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 官网

https://github.com/max0x7ba/atomic_queue

## 许可证

MIT

## 特性

- header-only 库（CMake INTERFACE target，无编译产物）
- 提供多种队列变体：`AtomicQueue`、`AtomicQueue2`、`AtomicQueueB`、`AtomicQueueB2`（均在公共头文件中）
- cache-friendly 设计，支持 SPSC/MPMC 多线程场景
- C++14 标准，无外部运行时依赖
- `defs.h` 已原生支持 x86、aarch64、ARM、RISC-V、LoongArch 等架构

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 1.9.2 | built | 2026-08-20 | cmake | 0 |

## 已知平台问题

- CMake 不识别 HarmonyOS，配方以 `CMAKE_SYSTEM_NAME=Linux` 构建
- 上游单元测试依赖 Boost.Test，未在本适配中构建；test_package 自行覆盖核心 API 验证
