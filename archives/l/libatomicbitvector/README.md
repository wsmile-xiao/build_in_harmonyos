# libatomicbitvector

> 运行期确定大小的原子位图/位向量，header-only。

## 简介

libatomicbitvector 提供一个大小在构造时确定的原子位向量 `atomicbitvector::atomic_bv_t`，
所有位操作都是原子的、线程安全，可用于协调对固定数量实体的并行处理，每项仅占 O(1) 位。
它派生自 Facebook folly 的 `ConcurrentBitSet`，用一层包装让原子类型可放入 `std::vector`。

```cpp
#include <atomic_bitvector.hpp>

atomicbitvector::atomic_bv_t x(1000);
x.test(100);          // false
x.set(100);           // false（返回旧值）
x.test(100);          // true
x.reset(100);         // true（返回旧值）
```

## OHOS 适配要点

- header-only：包内只安装 `include/atomic_bitvector.hpp` 与 `include/iterator_tpl.h`，
  被引用为 `#include <atomic_bitvector.hpp>`，无 `.a`/`.so` 产物。
- 无外部依赖；原子类型按平台自动选择 lock-free 的最大整型。
- 上游无测试套件（只有 `src/main.cpp` 并发演示程序）；本包在 `test_package` 中用 13 项
  检查覆盖 API 语义、迭代与并发写。
- CMake 目标：`atomicbitvector::atomicbitvector`。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | 仅 C++ 标准库 |

## 参考

- [源码仓库](https://github.com/ekg/atomicbitvector)
- [上游 README](https://github.com/ekg/atomicbitvector/blob/master/README.md)
