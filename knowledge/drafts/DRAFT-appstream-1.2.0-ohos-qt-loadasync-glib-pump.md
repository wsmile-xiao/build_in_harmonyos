# DRAFT-appstream-1.2.0-ohos-qt-loadasync-glib-pump — qtbase 无 QEventDispatcherGlib → QTimer 泵迭代 GLib 默认主上下文（Qt Pool::loadAsync）

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: build / qt / glib / event-loop
> **Audience**: Qt 项目消费 GLib 异步 API（g_task/g_async 系列）而 qtbase 未编译 glib 事件集成的平台

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R03）：as-test_qt-pool testLoadAsync
  `loadedSpy.wait()` 超时（5s 内未收到 loadFinished）。

## 症状（symptom）

```
FAIL!  : PoolReadTest::testLoadAsync() 'loadedSpy.wait()' returned FALSE.
```

GLib 异步完成回调（pool_ready_async_cb）从不被调度；Qt 信号永不发出。
同步 load()（testRead01）正常——差异只在异步路径。

## 机制（root cause）

`as_pool_load_async` 用 `g_task_run_in_thread`，完成回调挂默认 GMainContext 的
idle source。桌面 Linux 的 qtbase 编译了 QEventDispatcherGlib，Qt 事件循环会迭代
GLib 主上下文；OHOS 的 qtbase 未编译该集成，纯 Qt 事件循环（QTest/QEventLoop）
从不迭代默认 GMainContext → 回调悬挂。

## 修复（fix）

0009-qt-loadasync-glib-pump.patch：`Pool::loadAsync()` 启动 0ms QTimer 泵，
每个 Qt 事件循环 tick 调一次 `g_main_context_iteration(NULL, FALSE)`；GLib 回调
触发（emit loadFinished）后停泵。另在 generate() 注入 qtbase-pc-fix（重写
Qt6*.pc prefix 为已装包路径）+ qmake6/moc/rcc PATH + qt6.pc 转发。

## 验证（verification）

- as-test_qt-pool 1/1 OK、as-test_qt-misc 1/1 OK（meson test 2/2，rc=0）
- create60 全量 11/11 通过。

## 适用边界 / 反例

- 适用：Qt 应用/测试事件循环需驱动 GLib 异步回调、qtbase 无 glib 集成；
- 反例：qtbase 已编译 QEventDispatcherGlib 时无需泵；仅同步 GLib 调用不适用。

## 关系

- 查重：grep "g_main_context_iteration|QEventDispatcherGlib|QTimer.*glib" 无命中；
  E189/E441/E542/E323/E437 为 Qt 组件解析（无关）。
- similar_to: []；caused_by: []；prerequisite_of: []；conflicts_with: []

## 证据

- 补丁：patches/0009-qt-loadasync-glib-pump.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 11
