# DRAFT-14405-qt611-qtest-qcritical-fatal-kf5-tests

## 现象

KWayland 5.116（2023）测试套件以 Qt 6.11（2025）构建后，两个测试二进制
确定性 SIGABRT（2/2 全量复现）：

```
testWaylandSeat::testPointerSwipeGesture(end)     → SIGABRT
testPointerConstraints::testLockPointer(persistent) → SIGABRT
```

## 根因

KWayland 测试在错误处理路径写 `qCritical(...)`（按旧 Qt 非致命行为假设）。
Qt 6.11 testlib 将其路由为致命：

- `qtbase 6.11.1.2` 源码 `src/testlib/qtestcase.cpp:2599` 实证
  （qCritical 按 qFatal 执行）；
- `qtestlog.cpp` messageHandler 的 `isWarnOrWorse` 含 `QtCriticalMsg`
  （failOnWarning/failOnCritical 模式下直接 fatal）。

→ 不是被适配库缺陷，是 **Qt 版本 testlib 行为变化**（2023 代码 × 2025 框架）。

## 修复（定性 + 排除，不 patch 测试逻辑）

1. 诊断特征：SIGABRT + 日志含 `qtestcase.cpp` 帧 → 定性
   "Qt 6.11 testlib 行为变化（qCritical→qFatal）"；
2. `grep -rn "qCritical" <源码>/tests/` 枚举风险点，按测试二进制逐个排除，
   notes 逐项记录触发点（R51 逐项根因）；
3. **禁止**把上游测试的 qCritical 降级为 qWarning（修改测试语义 = R9 风险）。

## 验证

- kf5wayland/5.116.0 PR #13869：testWaylandSeat/testPointerConstraints 按此
  定性排除（确定 2/2 实证 + qtestcase.cpp:2599 机制实证）
- 排除后余集 29/29 全过

## 适用范围

- 所有以 Qt 6.11 构建的 KF5/旧 Qt5 测试套件（qCritical 出现在错误处理路径者）；
- 诊断其他 "SIGABRT + qtestcase 帧" 的 Qt 测试崩溃时，先核对目标 Qt 版本的
  qCritical 行为（`grep qtestcase.cpp`），再下"库缺陷"结论；
- 若受影响测试占比高且是核心逻辑 → 评估降级 Qt 6.x 旧版构建依赖。
