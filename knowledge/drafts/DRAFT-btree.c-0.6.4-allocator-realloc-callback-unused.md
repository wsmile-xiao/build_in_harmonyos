# DRAFT-btree.c-0.6.4-allocator-realloc-callback-unused — 自定义分配器回调声明≠调用：realloc 回调上游从不调用

- 触发事件：btree.c 0.6.4（tidwall/btree.c）首轮适配的鸿蒙专项测试组 2
  首跑 FAIL——测试断言 `btree_new_with_allocator` 的 realloc 回调计数 > 0，
  实际库内从不调用该回调。
- 路径：Path B（知识库扩展）
- 编号：DRAFT-btree.c-0.6.4-allocator-realloc-callback-unused

## 现象

为带自定义分配器 API 的 C 库编写鸿蒙专项测试时，测试断言分配器回调调用
计数：malloc>0、realloc>0、free>0。首跑失败：`OHOS_TEST_RESULT: FAIL
(1 group)`，仅 realloc 计数断言未通过（运行日志
archives/b/btree.c/0.6.4/reports/logs/ohos-test.log 首版
SHA-256 b1108603211d67c1881c515e03bf9d3ddb4ec2276125571c95daf1049a98ba8d）。

## 根因

API 声明 ≠ 库真实调用路径。btree.c 的 `btree_new_with_allocator` 签名声明
`void *(*realloc)(void *, size_t)`，但实现内部明确标注
`(void)realloc_; // realloc not used`——节点分配只走 malloc，节点释放只走
free，从不调用 realloc。测试误以为节点分裂/扩容会触发 realloc 路径，
将"API 声明"当成了"实现调用"。

## 修复（已在本轮验证）

测试去除 realloc 计数断言，仅断言 malloc/free 真实调用，并在注释中记录
"realloc 回调上游不调用"。修正后 `OHOS_TEST_RESULT: PASS`（3/3 组，
exit 0，malloc=395 realloc=0 free=395，日志 SHA-256
0d7ddd6bedbb9f0fcfd92ed6c68e6e2f851d40922d23e0a7dbf1ea9b69e43bd9）。

## 验证

- 断言修正前后对比：FAIL（realloc 断言）→ PASS（去掉 realloc 断言），
  同一测试程序仅改动断言集合，其余 2 组不受影响。
- malloc=395 / free=395 计数证明自定义分配器真实接入 OHOS libc allocator；
  realloc=0 印证源码注释"realloc not used"。

## 适用边界 / 反例

- 适用：为带自定义分配器/回调 API 的 C 库编写测试时，先核对源码确认每个
  回调的真实调用路径（grep 实现体），只对真实调用的回调断言计数；
  分配器回调计数的意义在于"分配器真实被接入"，不是"每个 API 参数都被调用"。
- 反例/边界：若回调由库在特定代码路径调用（如扩容 realloc），断言仍有效；
  断言前必须以源码或实测为准，不得凭 API 签名推断。

## 关系

- similar_to: []（四范围查重未命中）
- caused_by: []
- prerequisite_of: []
- conflicts_with: []