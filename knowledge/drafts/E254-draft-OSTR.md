# E254 - 监控型程序在 OHOS 上应把单项指标失败降级为部分数据

> **结构化数据**: [E254-draft-OSTR.kv](E254-draft-OSTR.kv)
> **类别**: system-monitoring/runtime/portability | **严重度**: 🟡 | **阶段**: runtime/testing

## 症状

一个监控型程序已经能启动，但只要某个指标探针失败，整个命令就直接返回失败，或者把本来还能拿到的其余指标也一并丢掉。

## 根因

这类程序常把 CPU、内存、load、hostname、磁盘等探针串成一条成功链。OHOS 上，个别 `/proc` 读取、`sysinfo()`、`getloadavg()` 或磁盘探测可能不可用，单点失败不该拖垮整机输出。

## 修复

把每个探针拆成独立边界：

1. 先把结果初始化为安全默认值。
2. 单项失败只跳过对应字段。
3. 只有启动失败或数据格式损坏才 fatal。

## 验证

- `conan create`
- `test_package`
- 手动运行时仍能输出可用指标

## 关系

- `similar_to -> E031`，但这里强调的是多指标聚合的降级策略。
