# DRAFT — rpmalloc 1.4.5 aarch64 弱内存序下 deferred free 链表 relaxed CAS 竞态

- 时间: 2026-09-08
- 软件: rpmalloc 1.4.5
- 门禁: 上游测试 test_crossthread（HarmonyOS PC / OHOS arm64, clang 15, -O2/-O3）
- 状态: UNMATCHED（本地快照扫描无等价命中，需审核提升为 E 条目）

## 问题

rpmalloc 1.4.5 官方上游测试二进制在 OHOS arm64（clang 15.0.4、-O2/-O3）下运行
`test_crossthread` 时，`rpmalloc_finalize()` 触发断言：

```
Assertion failed: (atomic_load32(&_mapped_pages) == 0) && "Memory leak detected"
(rpmalloc/rpmalloc.c: rpmalloc_finalize: 3034)
```

现象特征：
- -O0 构建通过，-O2/-O3 确定性失败（优化敏感）
- 失败与线程数相关（2/4/16 线程失败、8 线程通过），属时序竞态
- ASan 构建额外暴露 "Linked list corrupted"（`_rpmalloc_span_double_link_list_remove: 1105`）
- 统计转储显示 finalize 时仍有大量 span 未 unmap（MappedMiB 数千）

## 根因

rpmalloc 1.4.5 的跨线程释放路径 `_rpmalloc_deallocate_defer_free_span()` 把完全释放的
span 推入 owner heap 的 `span_free_deferred` 链表：

```c
do {
    span->free_list = (void*)atomic_load_ptr(&heap->span_free_deferred);
} while (!atomic_cas_ptr(&heap->span_free_deferred, span, span->free_list));
```

其中 `atomic_cas_ptr` 使用 `memory_order_relaxed`：

```c
atomic_compare_exchange_weak_explicit(dst, &ref, val, memory_order_relaxed, memory_order_relaxed)
```

而消费者（owner 线程）用 `atomic_exchange_ptr_acquire`（acquire 语义）取出整个链表。
在 x86（强内存序 TSO）上 relaxed CAS 与 acquire exchange 的组合碰巧可观测一致；但在
aarch64 弱内存序 + O2 优化下，生产者对 `span->free_list`（作为链表 next 指针）的写入
与 CAS 之间缺少 release 语义，消费者 acquire exchange 成功取出 head 后可能读不到
`span->free_list` 的新值，链表 next 指针损坏 → 双向链表断言失败 / span 永远无法
unmap → finalize 时 `_mapped_pages != 0` 报 "Memory leak detected"。

上游 2.0 完全重写分配器内核（per-page deferred free list）解决了 1.4.x 这一系列问题，
但 1.4.5 作为 1.4 系列终版无后续补丁，需在适配中修复。

## 方案

把 `atomic_cas_ptr` 从 relaxed 升级为 acq_rel/acquire（该 helper 的唯一调用点正是
deferred span 入链，升级不改变其他路径语义）：

```c
atomic_compare_exchange_weak_explicit(dst, &ref, val, memory_order_acq_rel, memory_order_acquire)
```

- 成功时 acq_rel：保证先前的 `span->free_list` 写入以 release 发布，与消费者的
  acquire exchange 正确同步（synchronizes-with）
- 失败时 acquire：重试循环中读到最新链表头
- 该修复最小、可逆，且不影响分配器热路径上的其他 relaxed 计数操作

## 验证

- 修复前：`./bin/linux/release/arm64/rpmalloc-test` 在 test_crossthread 后
  finalize 断言失败（exit 134），-O2/-O3 确定性复现
- 修复后：完整上游测试套件全通过（`All tests passed`，exit 0），包含
  test_alloc/test_realloc/test_superalign/test_crossthread/test_threaded/
  test_threadspam/test_first_class_heaps/test_large_pages/test_named_pages/test_error
- conan-verify G2（干净构建 + test_package 消费者测试）通过

## 适用边界

- aarch64（及所有弱内存序平台）上使用 relaxed CAS + acquire exchange 配对推送/消费
  无锁链表的库
- 优化级别 -O2 及以上（-O0 因时序不同常掩盖问题）
- 内存分配器 / 无锁数据结构 / deferred free 类实现的跨线程释放路径

## 反例与限制

- 反例：x86/TSO 强内存序平台通常不触发（relaxed 与 acquire 在硬件上一致），不能据此
  断言无竞态；上游 CI 主要为 x86-64，故该问题未被上游发现
- 限制：本条目只修复了 `span_free_deferred` 入链的内存序；若库中其他路径存在独立的
  relaxed 计数/链表操作，仍需按各自同步需求单独审计，不能一概升级所有 relaxed
- 不应把 "-O0 通过" 当作免修复证据，也不应在配方中强制降优化来掩盖竞态
