# DRAFT: open_memstream 写回调崩溃改真实文件 — composefs 1.0.8 适配实证

## 问题
`tests/test-lcfs` 在 OHOS PC（clang 15）上确定性崩溃：未补丁前 SIGABRT（mkstemp 断言），
补丁 TMPDIR 后变 **SIGSEGV（-O0）/ SIGILL（-O1/-O2），多进程复跑 8/8 崩溃**；而带
fprintf 布局变化或 ASan/UBSan 构建偶发通过——崩溃随二进制/堆布局漂移。隔离实验：
`test_basic` 单测 8/8 崩溃、`test_basic+test_no_verity` 通过，指向 **testwrite_node 的
open_memstream 承载 EROFS 序列化输出（fwrite 回调 + 增长 buffer）路径**。

## 根因
鸿蒙 musl 的 open_memstream 实现缺陷族（E302/DRAFT-13533 已证 fclose 丢数据）；本候选
是其**崩溃表现**：写回调 + fwrite + 增长 buffer 模式在各优化级别下确定性 SIGSEGV/SIGILL。
等价真实文件写入（mkstemp+fdopen）20 次探针 0 崩溃。

## 方案
最小测试补丁：testwrite_node 的输出承载由 open_memstream 替换为真实临时文件
（mkstemp + fdopen，写后 fclose + unlink），保留文件回调接口与 EROFS 写语义。

## 验证（本轮真实日志）
- 隔离实验：test_basic 单测 -O1 8/8 崩溃；等价位（memstream vs tmpfile）探针 20 次：
  memstream 崩溃、tmpfile 0 崩溃
- 补丁后：tests/test-lcfs 5 个子测试全过，3/3 复跑 exit 0

## 适用边界
- 适用：OHOS PC 上以 open_memstream 作输出承载（写回调增长模式）的测试/工具
- 反例：库自身必须用内存承载的场景，不能无脑替换——先用行为探针（E302）验证
  write/fclose/flush 契约，契约不可用再禁用或替换

## 查重差异（七轴摘要）
| 轴 | 结论 |
|---|---|
| exact_duplicate | 否 |
| causal_duplicate | 与 E302/DRAFT-13533-ohos-musl-open-memstream-fclose **同根因**（鸿蒙 musl open_memstream 缺陷） |
| trigger_overlap | 部分（既有条目=丢数据；本候选=写回调增长模式崩溃） |
| solution_overlap | 部分（既有=fflush/行为探针禁用；本候选=真实文件替换） |
| combination_novelty | 是（崩溃表现 + 真实文件替换） |
| boundary_novelty | 是（崩溃随布局漂移的边界；tmpfile 替代稳定） |
| test_migration_novelty | 是（test-lcfs 实测迁移） |

关系：similar_to=E302, DRAFT-13533-ohos-musl-open-memstream-fclose；无 prerequisite/conflicts。
