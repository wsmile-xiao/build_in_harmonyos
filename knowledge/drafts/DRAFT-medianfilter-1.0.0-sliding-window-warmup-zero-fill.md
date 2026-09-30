# DRAFT-medianfilter-1.0.0-sliding-window-warmup-zero-fill：滑动窗口中值滤波器 warmup 语义（窗口未满 0 填充）对测试/消费者断言的影响

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-28
> Source: medianfilter 1.0.0 适配（accabog/MedianFilter，OHOS arm64）
> 对应：`knowledge/drafts/DRAFT-medianfilter-1.0.0-sliding-window-warmup-zero-fill.kv`

## 现象

适配滑动窗口类滤波/统计库（如 MedianFilter：`MEDIANFILTER_Insert` 维护滑窗中值）
并独立编写测试或消费者断言时，窗口**未满**阶段的输出与"满窗中值"直觉不一致：

```console
# 窗口 3，序列 {5,5,100,5,5,100,5}，逐点输出：
spike output[0]=0 expected 5    # ← 首个输出不是 5
```

即第 0 个采样插入后窗口只含 1 个有效样本 + 2 个零填充槽位，中值为
median(0,0,5)=0，而非 5。

## 根因

滑动窗口实现为**固定容量环形缓冲**，窗口未满时未使用槽位以 0 值初始化并参与
排序/中值计算（warmup 语义）。上游自带的测试（如 stress_test/circular_test）已
按同一语义建模（reference_median 显式把未满槽位填 0），但**独立撰写的
测试/消费者断言**若不复制该约定，就会把 warmup 输出误判为失败。

## 修复（已验证）

断言显式建模 warmup 语义：窗口大小 N，前 N-1 个输出按
`median(0,0,…,0, s1..sk)` 推导；满窗后才进入常规滑窗中值。

```c
/* w=3: output[0]=median(0,0,5)=0, output[1]=median(0,5,5)=5, i>=2 全满窗 */
if (out[0] != 0) return fail;          /* warmup 0 填充 */
for (int i = 1; i < 7; i++) if (out[i] != 5) return fail;
```

验证：medianfilter test_ohos H4（`w=3` 尖峰序列全 5，warmup 首输出 0）与
consumer_sensor.c（`w=5` ADC 序列，首满窗口中值=1005）均通过（exit 0）。

## 适用范围与边界

- 适用：滑动窗口中值/均值/排序窗类算法库的测试与消费者用例设计（OHOS 及通用）。
- 边界/反例：若库文档明确"未满窗口不产生输出"或"以特定哨兵填充"，则断言须按
  该库约定；C++ 模板类型 T 非整数时"0 填充"具体值以 T(0) 为准。

## 查重差异

- combination_novelty: yes（滑窗 warmup 语义 + 独立断言设计组合，知识库无
  既有滑窗滤波条目）。
- boundary_novelty: yes（窗口未满边界是最小新意、最易踩坑点）。
- test_migration_novelty: yes（上游测试自带该语义，但跨库迁移到独立消费者/鸿蒙
  专项测试时须自行复刻）。
- 关系: prerequisite_of=滑窗类库消费者/测试断言设计; caused_by=环形缓冲
  零初始化实现约定。