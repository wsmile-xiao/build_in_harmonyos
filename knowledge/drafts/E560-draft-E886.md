# E560 — OHOS libc++15 无 std::pmr 实现：pmr 后备分配器必须在库内等价降级

## 错误特征

```
taskflow/utility/object_pool.hpp:6:10: fatal error: 'memory_resource' file not found
```

若改成包含 `<experimental/memory_resource>` 并改写命名空间，则第二跳失败：

```
error: no type named 'synchronized_pool_resource' in namespace 'std::experimental::pmr'
error: no member named 'pool_options' in namespace 'std::experimental::pmr'
```

## 触发条件

- 构建系统: cmake（OHOS Conan profile，`os=OHOS`、`compiler=clang 15`、`libc++`）
- 阶段: 编译期（消费者翻译单元包含库头文件时）
- 平台: OHOS SDK `ohos-sdk_26.0.0.18`（libcxx-ohos 定制 libc++ 15）

## 根因分析

OHOS SDK 的 libc++ 15 是裁剪变体，存在三重缺口：

1. 公共头目录 `libcxx-ohos/include/c++/v1/` 没有 `<memory_resource>`；全 SDK 只有
   `experimental/memory_resource`（另一份 `include/c++/v1/` 同样没有）。
2. `libc++.so` 不导出任何 `std::pmr` 符号：
   `nm -D --defined-only libc++.so | grep -c pmr` = **0**；pmr 实现只存在于
   `libc++experimental.a`（23 个 pmr 符号）。
3. `experimental/memory_resource` 只提供 Library Fundamentals v1 的
   `memory_resource` / `polymorphic_allocator`，**没有** C++17 的
   `synchronized_pool_resource` / `unsynchronized_pool_resource` / `pool_options`
   （实测编译该命名空间下的 pool 资源直接报 `no type named ...`）。

因此本模式与“缺失标准头、但库并未真正使用该类型”的形态（jsonifier 实测，见
`knowledge/drafts/DRAFT-jsonifier-ohos-libcxx-missing-std-headers.md`）**不同**：
用 `__has_include` 守卫包含、或把 `std::pmr` 换成 `std::experimental::pmr`、或链接
`libc++experimental.a`，都不能让真实使用 pmr 类型的库编译通过或运行正确。

taskflow 4.1.0 的命中点是 `tf::ObjectPool`（`tf::Graph` 的节点池，所有消费者必经）：
冷路径成员是 `std::pmr::synchronized_pool_resource _backing{std::pmr::pool_options{
.max_blocks_per_chunk = 1024, .largest_required_pool_block = sizeof(Block)}}`，
并在热路径空闲栈为空时调用 `allocate/deallocate`、在 `release()` 时整块归还。

## 解决方案

### 推荐方案

特性探测 + 库内等价实现（不做平台宏判断）：

```cpp
#if defined(__has_include)
  #if __has_include(<memory_resource>)
    #define TF_HAS_STD_PMR 1
  #endif
#endif
#ifndef TF_HAS_STD_PMR
  #define TF_HAS_STD_PMR 0
#endif
```

- 具备 pmr 的标准库：保持原生 `std::pmr` 路径不变；
- 不具备时：在库内提供接口子集等价、行为等价的实现。以 taskflow 为例，
  `tf::SynchronizedBlockPool` 只暴露 `ObjectPool` 真正调用的
  `allocate(bytes, alignment)` / `deallocate(p, bytes, alignment)` / `release()`，
  内部是互斥保护的固定块空闲链表，按上游同样的 1024 块粒度成块增长
  （保留“一次加锁摊薄整块”的冷路径语义），超过池化尺寸或更严格对齐的请求直接
  走 `::operator new`（与 `polymorphic_allocator` 的上游回退一致），调用点不改。

修复证据（taskflow 4.1.0，设备原生）：34/34 测试可执行构建成功，
`ctest --output-on-failure -j1` 注册 2909 项全部通过；消费者 test_package 额外做
8 轮 × 5000 节点的图 churn（共 40000 次节点执行）覆盖后备池的增长与回收。

### 禁止做法

- ❌ 用空 stub、`return nullptr`、固定成功返回或删除调用点“绕过”缺失的 pmr —— 冷路径分配
  在运行时未定义，属伪修复。
- ❌ 直接 `-I .../libc++experimental` / `-lc++experimental` —— 该库只有
  `experimental::pmr`，不含 pool resource，不能提供 `std::pmr`。
- ❌ 把 `std::pmr` 改写成 `std::experimental::pmr` 就认为解决 —— 第二跳必然失败。

## 验证

```bash
SDK=${OHOS_SDK:-/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm}
find "$SDK" -name memory_resource                          # 只有 experimental/memory_resource
nm -D --defined-only "$SDK/lib/aarch64-linux-ohos/libc++.so" | grep -c pmr   # 0
clang++ -std=c++20 -c probe.cpp    # probe 包含 <memory_resource> → file not found
```

修复后：库的消费者可编译并通过上游测试（taskflow 实测 2909/2909）。

## 关联条目

- 相似: E130（libcxx-ohos 定制标准库；本条是其“缺失头但真实需要实现”的具体形态）
- 同族草稿: `knowledge/drafts/DRAFT-jsonifier-ohos-libcxx-missing-std-headers.md`
  （仅缺失头 + 未使用类型，修复只需包含守卫）
