# clips 6.30 DestroyEnvironment agenda 死循环（草稿）

- **来源**：clips 6.3（上游 6.30）适配，真机 test_package 第 2 轮挂起排障
- **日期**：2026-09-08
- **证据**：`archives/c/clips/6.3/notes.md`（A/B/C/D 表征矩阵）

## 现象

对已经产生规则激活（activation）的环境调用 `DestroyEnvironment` 后进程
**纯 CPU 空转不返回**（无内存增长、无 IO），只能外部 kill / timeout。

## 表征矩阵（真机 -O0 调试程序 + `timeout 15`）

| 场景 | DestroyEnvironment | 结论 |
|---|---|---|
| A: fresh env 直接销毁 | 返回 1 | teardown 机制本身可用 |
| B: 定义模板+规则，无事实匹配后销毁 | 返回 1 | 静态规则网络无碍 |
| C: reset+assert 产生 pending activation 后销毁（未 run） | **死循环** | 触发条件 = agenda 非空 |
| D: run 触发规则后销毁 | **死循环** | 同上 |

## 定性

- 上游 CLIPS 6.30 引擎 cleanup 路径缺陷；与 `-DLINUX`/OHOS/musl 无关
  （cleanup 代码无平台分支）。
- 随包 `clips` CLI 不受影响：`main.c` 注明控制流不从 CommandLoop 返回，
  从不销毁环境。
- 6.31 / 6.4x 是否修复未验证。

## 规避

- test_package / 消费者：不对已产生激活的环境做 teardown，另建 fresh env
  验证 `DestroyEnvironment` API（返回 1）。
- 若必须销毁：先确保 agenda 清空再销毁（未验证，谨慎）。
