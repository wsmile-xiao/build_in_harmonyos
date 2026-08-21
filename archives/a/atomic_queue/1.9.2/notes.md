# atomic_queue 1.9.2 适配笔记

## 库简介

atomic_queue 是一个高性能 C++ lock-free 并发队列库，由 Maxim Egorushkin 开发，MIT 许可证。

- GitHub: https://github.com/max0x7ba/atomic_queue
- 版本: v1.9.2 (commit c3eeb3d7bf85e8a6414294f5510681b7a595f97c)
- 构建系统: CMake (也提供 meson.build 和 Makefile)
- C++ 标准: C++14
- 许可证: MIT

## 适配特点

### header-only 库

库的核心是 5 个头文件：

- `include/atomic_queue/atomic_queue.h` — 主模板 (AtomicQueue, AtomicQueueB, AtomicQueue2, AtomicQueueB2)
- `include/atomic_queue/atomic_queue_mutex.h` — mutex-based 退化实现
- `include/atomic_queue/barrier.h` — 线程同步 barrier
- `include/atomic_queue/defs.h` — 平台定义 (CACHE_LINE_SIZE, spin_loop_pause)
- `include/atomic_queue/spinlock.h` — spinlock 实现

CMake 项目定义 `atomic_queue` 为 INTERFACE library，不产生 .a/.so 产物。

### 平台兼容性

- `defs.h` 已原生支持 `__aarch64__` 和 `__arm__` 架构
- ARM64 使用 `yield` 指令作为 spin_loop_pause
- `ATOMIC_QUEUE_FULL_THROTTLE` 在非 x86 上默认为 0（使用 atomic 而非 asm barrier）
- 无需 OHOS 特定 patch

### 测试策略

- 上游测试 `src/tests.cc` 共 9 个 BOOST_AUTO_TEST_CASE（含模板实例化 ~46 变体），依赖 Boost.Test
- 作为 header-only 库，不值得仅为测试引入 Boost 依赖
- **已移植 9/9 上游用例**到 test_package（无 Boost，100% 覆盖）：
  1. `stress` → `test_stress_mpmc`（3P/3C MPMC 求和校验）+ `test_stress_spsc`（1P/1C SPSC）
  2. `move_only_element` → `test_move_only_element`：unique_ptr 与 AtomicQueueB2
  3. `allocator_constructor_only_b` → `test_allocator_constructor_b`：stateful allocator
  4. `allocator_constructor_only_b2` → `test_allocator_constructor_b2`：stateful allocator + unique_ptr
  5. `move_constructor_assignment` → `test_move_constructor_assignment`：move 语义验证
  6. `try_push_pop` → `test_try_push_pop`：try_push/try_pop/was_empty/was_full/was_size/capacity
  7. `size` → `test_size`：RetryDecorator + capacity rounding
  8. `power_of_2` → `test_power_of_2`：10 个 static_assert 编译期检查
  9. `remap_index` → `test_remap_index`：RemapXor/RemapAnd 双射性和自反性
- benchmarks.h 中的 `CapacityArgAdaptor`、`RetryDecorator` helper 已内联实现到 test_package

### CMake 选项

| 选项 | 默认 | 适配设置 | 说明 |
|------|------|----------|------|
| ATOMIC_QUEUE_BUILD_TESTS | OFF | OFF | 需要 Boost.Test |
| ATOMIC_QUEUE_BUILD_EXAMPLES | OFF | OFF | 不需要 |
| ATOMIC_QUEUE_ENABLE_INSTALL | OFF | ON | Conan cmake.install() 需要 |

## W0 依赖检查

**无运行时依赖**。header-only 库，C++14 标准库是唯一依赖。

上游测试依赖 Boost.Test，但未在本适配中构建。所有 9 个上游测试用例已移植到 test_package（无 Boost 依赖）。
