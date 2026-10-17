# DRAFT — lfqueue 1.2.2 single-deq 立即 free(head) 竞态：最小修复补丁

> 草稿（路径 B 知识候选），随 lfqueue 1.2.2 归档同 PR 交付。
> 关联 .kv: `DRAFT-lfqueue-1.2.2-single-deq-race.kv`
> 状态：R02 已实施最小修复补丁（patches/0002-single-deq-delayed-recycle.patch）并通过全量验证。

## 问题

Taymindis/lfqueue 1.2.2 的上游自测程序 `lfqueue-example`（CMake `add_test lfqueue_test`）
在 `one_deq_and_multi_enq` / `one_deq_must_and_multi_enq`（多生产者 + 单消费者）场景
**修复前 5/5 次运行挂起**：进程进入 `STAT=S`（睡眠等待），不打印 `Test Pass!`，
`timeout 60` 返回 124（挂起点轮次随机：21/43/7/28/42，竞态特征）。同程序的单 enq + 多 deq
场景（`one_enq_and_multi_deq` / `one_enq_and_multi_deq_must`）**50/50 稳定通过**。

## 根因

`lfqueue.c::_single_dequeue()` 在 `CAS(head→next)` 成功后**立即 `free(head)`**；并发
`_enqueue()` 先读 `tail` 再执行 `CAS(&tail->next, NULL, node)`，成功后仅 best-effort 推进
tail（`__LFQ_BOOL_COMPARE_AND_SWAP(&lfqueue->tail, tail, node)`，失败不回补）。队列空/近空时：

1. 消费者 CAS 把 head 推进并释放被并发生产者仍可能引用的旧 head 节点；
2. 生产者已读取的 `tail` 可能仍指向该（已释放的）节点，其 `CAS(&tail->next, ...)` 或
   重读 tail 踩已释放内存 → 链断裂/活锁；
3. 单消费者在 `lfqueue_sleep(1)` 中永远等不到新项 → 挂起。

多消费者路径 `_dequeue` 不立即 free，而是进 `__lfq_recycle_free` 延迟 free-list
（`__lfq_check_free` 2 秒后才释放），因此多消费者场景不触发——这解释了"为什么只有
single-deq 场景挂"。

## 最小修复补丁（本库实施，patch 0002）

不改变公开 API 签名与语义，不改动上游测试程序；把 `_single_dequeue()` 的立即 free 改为
与多消费者路径 `_dequeue` 完全一致的延迟回收：

```diff
--- a/lfqueue.c
+++ b/lfqueue.c
@@ -163,7 +163,7 @@
 				if (next) {
 					val = next->value;
 					if (__LFQ_BOOL_COMPARE_AND_SWAP(&lfqueue->head, head, next)) {
-						free(head);
+						__lfq_recycle_free(lfqueue, head);
 						break;
 					}
@@ -172,6 +172,9 @@
 			}
 		}
 	}
+
+	__LFQ_SYNC_MEMORY();
+	__lfq_check_free(lfqueue);
 	return val;
 }
```

机制要点：

- `__lfq_recycle_free`：把出队节点挂入共享延迟 free-list（`move_free` 链），记录时间戳，
  CAS 追加，不立即释放；
- `__lfq_check_free`：仅在延迟 >2 时间单位后释放，覆盖并发生产者 tail 引用的存活窗口；
  `_enqueue()` 本身也调用它，因此单消费者+多生产者下 free-list 持续被排空，内存不会泄漏；
- 队列初始化（`lfqueue_init`）已创建 `root_free`/`move_free` 哑节点，与 `_dequeue` 共用，
  补丁零新增数据结构。

## 验证（修复前后对照）

| 项 | 修复前 | 修复后 |
|---|---|---|
| 上游 lfqueue-example | 5/5 挂起（`timeout 60` → 124，STAT=S） | 5/5 `Test Pass!` 退出 0（`timeout 120`） |
| ctest lfqueue_test | 挂起超时 | 1/1 Passed（53.67s） |
| 消费者 test_package/test.c | PASSED（deq_must 规避路径） | PASSED 无回归：enq 10 万 + deq_must 10 万，sum=4999950000，size=0，exit 0 |
| conan-verify G1-G4 | PASS | PASS（双补丁 0001+0002 经 conandata.yml 应用） |
| finish W2/W3 | W2/W3 通过 | W2 仅配方变更（11 文件无框架）、W3 100% 1/1 PASS |

双口径统计：source_declared_total=1、configured_executable_total=1、executed_passed_total=1、
full_rate=1/1 (100%)。

## 适用边界与反例

- **适用**：任何"多生产者 + 单消费者"下使用锁自由队列且 dequeue 立即 free 的实现；
  修复思路（出队节点进延迟回收列表，与既有多消费者回收路径对齐）可跨库复用
  （Taymindis 同源 lfstack 等手写 CAS 队列）。
- **边界**：延迟回收使单消费者路径与多消费者路径共享同一 free-list 与 2 秒延迟窗口，
  单消费者负载下限（dequeue 频繁、无并发 enqueue）时 `__lfq_check_free` 仍被 dequeue
  自身调用，free-list 正常排空。
- **反例**：修复前"单生产者+单消费者"或"多消费者"本就不触发；修复后"任意生产者数 +
  单消费者"均实测通过。不可用场景：未应用本补丁且队列存在空窗的多生产者+single_deq。

## 查重（七轴，R02 更新）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false（无同库同版本同错误/同修复条目） |
| causal_duplicate | false（无同根因条目：E399 仅 ctest 行为、E103 仅 CMake 版本） |
| trigger_overlap | false（lock-free 挂起 vs ctest 行为 vs cmake 版本，触发面不重叠） |
| solution_overlap | false（延迟回收对齐既有 _dequeue 路径 vs BUILD_TESTING vs bump 版本，方案不重叠） |
| combination_novelty | true（立即 free + 并发 tail-CAS 组合及"对齐既有延迟回收路径"的最小修复均无登记） |
| boundary_novelty | true（新边界：single-deq 仅在延迟回收下对多生产者安全） |
| test_migration_novelty | true（修复前后对照 + 双口径台账 + deq_must 恰好消费校验范式可跨库复用） |

## 与既有条目关系

- similar_to: E399（ctest 行为类，弱相似）
- caused_by: 上游 lock-free 实现缺陷（非本平台）
- prerequisite_of / conflicts_with: 无

## 路径决定

- 候选 2（CMake < 3.5）完整命中 E103 → 复用既有知识（path A 成分）。
- 候选 1 已从"仅规避"升级为"最小修复补丁 + 修复前后对照验证"，查重仍未命中、
  新增差异由本轮真实日志验证且可跨库复用 → **走路径 B：new_draft 判定不变
  （path_decision: path_b_new_draft）**，草稿随本库归档文件同 PR 交付。