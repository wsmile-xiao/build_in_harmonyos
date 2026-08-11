# E314: HarmonyOS setitimer(ITIMER_PROF) 初始延迟异常导致 Rprof 空事件，回退 RPE_ELAPSED

> **Contributor**: RBA1 | **Status**: DRAFT | **Created**: 2026-08-09
> **Severity**: medium | **Category**: runtime-capability

## 错误特征

R 4.5.1 上游测试 `tests/reg-tests-2.R` 中 Rprof memory profiling 回归测试块失败，报错信息如下：

```text
Error in Rprof_memory_summary(con, chunksize = chunksize, label = index, ...) :
  no events were recorded
```

该错误仅在 HarmonyOS 平台出现。同轮次的其他测试块（complex.R、lapack.R 等）均正常通过，说明数值计算功能本身未损坏，问题局限于 Rprof 采样的运行时能力。

## 触发条件

1. 在 HarmonyOS 设备上运行 `make -j1 check` 或单独执行 `tests/reg-tests-2.R`。
2. 测试进入 Rprof memory profiling 回归块，调用 `Rprof()` 以默认 interval=0.02s 启动采样。
3. R 内部使用 `RPE_CPU` 事件类型，通过 `setitimer(ITIMER_PROF)` 设置周期性 SIGPROF 定时器。
4. HarmonyOS 内核对该定时器的初始延迟处理异常：请求的 it_value=0.02s 被实际置为约 1.4s。
5. 首个 SIGPROF 信号远晚于 profiling 工作负载的结束时刻，采样事件数为 0。
6. `Rprof_memory_summary()` 检测到空事件，抛出错误。

## 根因分析

R 的 profiling 子系统默认采用 ITIMER_PROF（CPU 时间定时器）驱动 SIGPROF 信号进行采样。在标准 Linux 平台上，`setitimer(ITIMER_PROF, {it_interval=0.02, it_value=0.02})` 设置后，首个信号在约 0.02s CPU 时间后触发，后续以 0.02s 为间隔周期触发。

HarmonyOS 内核对该定时器的初始延迟处理存在平台差异：请求的 it_value=0.02s 被实际置为约 1.4s（约为请求值的 70 倍）。这意味着在典型的短时 profiling 工作负载（数秒内完成）中，首个 SIGPROF 尚未到来，工作负载已结束，`Rprof(NULL)` 关闭采样，导致 `summaryRprof()` 报告 0 个事件。

此问题属于平台运行时能力差异，不是 R 代码 bug 或数值功能损坏。同轮次 complex.R、lapack.R 等测试块均正常通过。

## 解决方案（含验证）

### 推荐方案：probe → detect → fallback（补丁 0008）

在 `R_InitProfiling` 中、`signal(SIGPROF, doprof)` 之后增加能力探测：

1. 以请求的 interval 设置 ITIMER_PROF。
2. 立即调用 `getitimer(ITIMER_PROF)` 回读实际 it_value。
3. 若回读的 it_value 大于请求值的 10 倍（`p_got > p_set * 10`），判定定时器异常。
4. 将 `R_Profiling_Event` 从 `RPE_CPU` 改为 `RPE_ELAPSED`，走既有 `ProfileThread`（`pthread_kill(SIGPROF)`）路径。
5. 探测完成后清零定时器（`setitimer(ITIMER_PROF, {0,0})`），不残留状态。

关键设计点：
- 能力探测不影响正常平台：HarmonyOS 之外的平台上 it_value 回读正常（约等于请求值），不会触发回退。
- 探测在 profiling 启动时一次性完成，无持续开销。
- 回退路径 `RPE_ELAPSED` + `ProfileThread` 是 R 已有的备选机制，通过线程内 `pthread_kill` 触发 SIGPROF，不依赖 ITIMER_PROF 的初始延迟行为。

### 验证

修复后 20/20 次重复采样均有事件（12-16 个），上游测试块 `reg-tests-2.R` 的 Rprof memory profiling 部分真实通过。Round 16 retry-03 完整 CI exit 0。

### CI 注意

此类运行时能力差异补丁在 CI 的 L4 "dangerous functions in patches" 检查中会 warn（`setitimer`/`signal` 被识别为危险函数），属适配必需，应记录而非误判为空壳。

## 互引说明

- **similar_to E176**: 两者均为 HarmonyOS 平台运行时能力差异导致的构建/测试问题。E176 是动态链接器拒绝加载 ICU stubdata；E314 是内核 ITIMER_PROF 初始延迟异常。修复策略均为平台能力探测后选择兼容路径。
- 与 E244（时区）、E245（SONAME）、E246（install sed）属同一 r-base 4.5.1 适配批次（Round 5-16），但解决的问题轴不同。
