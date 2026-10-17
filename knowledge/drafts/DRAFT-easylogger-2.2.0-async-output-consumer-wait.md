# DRAFT：异步输出日志库的 test_package 消费者测试——输出后等待 + 捕获校验

> Contributor: pc2-42（easylogger 2.2.0 适配） | Status: Draft | Updated: 2026-09-19
> Source: 任务 easylogger-2.2.0-r01-pc2-42（分支 feat/easylogger-2.2.0，PR 编号创建后回填）
> 对应图谱草稿: knowledge/drafts/DRAFT-easylogger-2.2.0-async-output-consumer-wait.kv

## 背景

EasyLogger 2.2.0 是嵌入式 C 日志库，默认 `elog_cfg.h` 开启
`ELOG_ASYNC_OUTPUT_ENABLE`（pthread + sem 后台线程消费日志环形缓冲）。
按 SKILL 门禁，test_package 必须真实调用公开 API 并校验可观察结果（R34/PF3），
不能只打印字符串。

## 症状（可复现）

conan-verify G2 首次失败：

```
ERROR: easylogger/2.2.0@ohpcd/stable (test package): Error in test() method
test_easylogger: captured=0 bytes
FAIL: missing marker assert-marker
FAIL: missing marker error-marker
...（全部 8 项断言失败）
```

test 编译链接成功、进程正常退出，但捕获缓冲为空。知识引擎初判建议 E298
（cmake.test() 委托 CTest 无法控制 conanrun 环境），实测与 E298 机制无关
（静态库 + 无运行环境依赖）。

## 根因

`elog_output()` 在 `ELOG_ASYNC_OUTPUT_ENABLE` 下先 `async_put_log()` 入环形缓冲，
由 `async_output` 线程 `sem_wait()` 后消费并调用 `elog_port_output()`。
test_package 在 `log_*` 宏返回后**立即**读取捕获缓冲 → 异步线程尚未消费，
缓冲为空。这是测试与异步消费线程的**时序竞态**，不是库缺陷，也不是环境/PATH 问题。

## 方案（可跨库复用）

1. **输出后显式等待**：test.c 中所有 `log_*` 输出后 `usleep(1000 * 1000)`（1s，
   远超异步线程消费延迟）再校验捕获缓冲。本地复现 500ms 后捕获 206 bytes 完整输出。
2. **port 捕获输出**：test_package 自实现 port，`elog_port_output()` 把日志
   memcpy 进内存缓冲（同时 printf 留证），断言各级别 marker 与版本横幅
   `EasyLogger V2.2.0` 均在捕获中出现。
3. **兜底（可选）**：编译期 `-DELOG_ASYNC_OUTPUT_ENABLE=0` 走同步直通路径
   （direct.c 验证 log_i/elog_raw 即时输出），消除时序依赖；代价是未覆盖
   真实消费者默认配置的异步行为，优先用等待模式。

## 真实验证

- 修复前: conan-verify G2 FAIL（captured=0，8 断言全失败）
- 修复后: conan-verify G2 PASS（ctest 1/1 Passed，8 断言全过）
- 鸿蒙专项测试 tests-ohos/ohos_test.c（异步默认配置）: 6/6 断言通过，
  `OHOS TEST PASS`（含级别/tag/keyword 过滤与输出开关行为）

## 适用边界与反例

- 适用: 默认开启异步输出线程的 C/C++ 日志库/嵌入式库；test_package 或
  消费者测试需校验日志输出内容的场景。
- 边界: 等待时长须覆盖消费延迟（一般 ≤1s；极端高负载下用等待+轮询或
  同步模式兜底）；输出量超过环形缓冲时旧日志会被丢弃，断言应只覆盖
  缓冲容量内最近的日志。
- 反例: 同步直通输出库（无 async 宏）无此竞态，无需等待；纯功能库
  （不输出日志）不适用本模式。

## 查重关系

- related_to: E298（同为 test_package test() 失败类别，但机制不同——
  E298 是运行环境/搜索路径，本条目是异步缓冲消费时序）
- similar_to: E001/DRAFT-stc-5.0-makefile-cflags-env-override（构建配置陷阱类别）
- 与本库同族: EasyFlash/cmBacktrace（armink 系）同类异步输出库可直接复用