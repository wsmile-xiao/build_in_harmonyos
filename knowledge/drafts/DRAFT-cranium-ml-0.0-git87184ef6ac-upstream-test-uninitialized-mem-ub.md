# DRAFT-cranium-ml-0.0-git87184ef6ac-upstream-test-uninitialized-mem-ub

上游测试未初始化堆内存读取在 -O3 下触发断言失败：用 -O0 vs -O3 对照 + 清零初始化对照，
把失败归因于上游测试自身 UB（库/平台无缺陷），如实计入失败项并给出恢复条件。

- 来源: cranium-ml 0.0-git87184ef6ac 适配（Path B 知识库扩展）
- 状态: 草稿（待审核 promote）
- 关联: E249（借用指针所有权标志 → invalid free 家庭）、E259（assert 副作用 NDEBUG）、
  E347（源码下载缓存预置）

## 错误特征

```
Assertion failed: .*(\.c: main: \d+)       # -O3/Release 下
Signal 6 (core dumped)
exit_code=134
```

## 根因

上游测试用 malloc 分配数据结构后只初始化部分元素（例：只置对角线），其余为未初始化堆内存；
库函数把数据拷贝进新矩阵后再做 `assert(a == b)` 相等断言。C 标准下读取未初始化内存是未定义行为，
-O3 优化下拷贝/读取可能产生不一致值导致断言失败，-O0 下两次读取一致、断言通过。
属"上游测试自身缺陷"，不是库、平台、工具链或适配问题。

## 诊断方法（可跨库复用）

1. **-O0 对照**：同一测试源用 -O0 编译运行，若全部断言通过 → 优化级别相关；
2. **清零初始化对照**：把数据结构全部显式初始化为 0 后再走库转换/断言，-O3 下若全部一致
   → 证明库逻辑正确、失败源于上游测试未初始化读取 UB；
3. 判定为上游测试缺陷，如实计入失败项（不记为通过、不修库、不打平台补丁），
   恢复条件 = 上游测试初始化全部元素；双口径台账中说明根因、对照命令、退出码。

## 验证（cranium-ml 实测）

- matrix_tests：-O3 断言失败（exit 134，`ds->data[i][j] == getMatrix(mds,i,j)` 行 83）；
- dbg_ds（清零初始化）：-O3 下 9 元素全一致，exit 0；
- dbg_ds2（复刻上游未初始化写法）：-O0 全一致，-O3 下 4 个未初始化元素不一致 → 确认上游测试 UB。
- 台账: archives/c/cranium-ml/0.0-git87184ef6ac/reports/upstream-test-ledger.md（4/5=80%）。

## 适用边界与反例

- 适用: C/C++ 上游测试 malloc+部分赋值后断言；-O3/Release 才暴露的测试失败；
  用于区分"上游测试缺陷"与"库/平台/适配缺陷"。
- 不适用: 库自身 invalid free/SIGSEGV（属 E249 所有权标志家庭）；
  依赖缺失/平台限制导致的失败需走依赖复查、TMPDIR 恢复等既有流程，不得套用本诊断。

## 查重关系

- similar_to: E249（trigger_overlap：未初始化内存家族；solution 不同——E249 修库所有权，
  本条目是测试诊断法）
- exact_duplicate: 否；causal_duplicate: 否；trigger_overlap: E249 部分；
  solution_overlap: 低；combination_novelty: 否；boundary_novelty: 是
  （-O0/-O3 对照定位上游测试 UB 的边界）；test_migration_novelty: 否
- path_decision: path_b_new_draft（新增差异已由本轮真实日志验证，可跨库复用）
