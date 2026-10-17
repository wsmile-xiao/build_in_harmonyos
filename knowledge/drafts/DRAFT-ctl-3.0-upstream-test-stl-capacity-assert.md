# DRAFT-ctl-3.0-upstream-test-stl-capacity-assert：STL 内部容量/桶数精确相等断言的评估

## 现象

ctl 3.0 上游 `tests/func/` 中两个用例在本环境（clang 15 / libc++17）确定性断言失败：

- `test_ust.cc: Assertion failed: a.bucket_count == b.bucket_count() (main: 79)`，10/10 失败
- `test_vec.cc: Assertion failed: a.capacity == b.capacity() (main: 142)`，10/10 失败
- `test_str.cc` 同源断言**偶发**命中 1 次（随机种子），独立重跑 10/10 通过

## 根因

上游测试把 ctl 容器与 C++ STL 容器逐次执行相同操作后的**内部 capacity /
bucket_count 精确相等**作为断言。容器内部容量与哈希桶数是**实现细节**：
ctl 采用 2 倍增长策略，libc++ 的 vector growth / unordered_set rehash 策略与其
不同，同序列后必然发散。断言失败 ≠ 数据错误。

独立探针（随机 push/insert/erase/resize 序列，只比较 size 与逐元素内容）5 次运行
全部 `data-consistent=yes`；346 次操作中 140 次容量发散但数据全对——证实失败
来自容量数值比较，而非容器逻辑缺陷。

## 评估方法（双口径台账）

1. 数据一致性探针定位归属：`data-consistent=yes` ⇒ 上游过度断言；
2. 真实退出码（134/Signal 6）如实记录，计入全量通过率**分母**、不计为通过；
   ctl：12 个独立用例 10 PASS / 2 FAIL ⇒ `10/12 = 83.3%`，
   另列当前配置可执行集通过率 `10/10 = 100%`；
3. flaky 项不凭单次运行省略：独立重跑 10 次记录真实结果（test_str 10/10 PASS）；
4. 报告写恢复条件：上游放宽容量精确相等断言，或改造为数据一致性断言。

## 适用边界与反例

- 适用：任一与 STL 容器逐次比较内部容量/桶数的上游测试，在 OHOS/libc++（与
  上游 CI 不同 stdlib）工具链下评估；
- 反例：数据内容（size/元素/顺序）不一致的失败是真缺陷，必须修复本库；
  只比较元素内容的断言不在本条目范围内。