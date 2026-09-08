# E553 — 随机文件 CLOSE 后 reopen 写 NULL 缓冲区段错误：分配条件按指针判空修复

## 问题概述

老式 C 语言随机文件 I/O 库（案例：bwbasic 2.20pl2 的 bwb_dio.c）中，对同一设备号
执行 `CLOSE` 再重新 `OPEN "r"` 后，`GET` 语句向 `dev_table[].buffer` 写入读取内容时
发生段错误。根因不在 GET 本身，而在 **OPEN 的缓冲区分配条件用错了判据**：
`previous_buffer` 标志（由 `mode == DEVMODE_CLOSED` 置位）表示"此前打开过"，但它
无法区分"缓冲区还在"与"缓冲区已被 CLOSE 释放"。

## 典型错误（bwbasic putget.bas，任务 #6153 实录）

```
10 OPEN "r", 1, "t9.dat", 48
20 FIELD 1, 20 AS r1$, 20 AS r2$, 8 AS r3$
30 LSET r1$ = "x"
40 PUT #1, 1
50 CLOSE #1
60 OPEN "r", 1, "t9.dat", 48        ' previous_buffer=TRUE → 跳过分配
70 FIELD 1, 20 AS r1$, ...          ' sbuffer = NULL + 0
80 GET #1, 1                        ' buffer[i] = fgetc(...) → 写 NULL
→ Segmentation fault (core dumped)
```

上游测试套件中的 putget.bas（双记录 FIELD/LSET/PUT/GET 往返）必现。

## 根因

- `bwb_close`：`FREE(dev_table[].buffer)` 并 `= NULL`（两半成对，正确）；
- `bwb_open`：`if ((mode == DEVMODE_RANDOM) && (previous_buffer != TRUE))` 才分配——
  reopen 时 `mode == DEVMODE_CLOSED` 置 `previous_buffer = TRUE`，分配被跳过，
  `buffer` 保持 NULL；
- `bwb_field`：`b->sbuffer = dev_table[].buffer + current_pos` → NULL 偏移；
- `bwb_get`：`buffer[i] = fgetc(...)` → 写 NULL 段错误。

## 修复（单处条件）

```c
- if (( mode == DEVMODE_RANDOM ) && ( previous_buffer != TRUE ))
+ if (( mode == DEVMODE_RANDOM ) && ( dev_table[ req_devnumber ].buffer == NULL ))
```

保留"复用未释放缓冲区"的原设计意图（指针非 NULL 即有效），同时覆盖 CLOSE 后
的场景。修复后 putget.bas 双记录往返通过，41 个上游脚本全部执行（53 项断言）：40 通过 + width 已知局限（WIDTH 语句上游未实现，非本缺陷回归）。

## 定位手法（最小 .bas 二分）

逐语句叠加复现脚本：OPEN "r" → +FIELD → +LINE INPUT → +LSET → +PUT → +CLOSE
→ +reopen → +GET。本例前五步全部正常，叠加 reopen+GET 即崩，锁定分配条件。
比在解释器 C 代码里盲找快一个数量级。

## 查重与新增价值

知识图谱 index.tsv 与既有草稿中无 use-after-NULL / 随机文件 reopen / bwb_dio /
previous_buffer 相关条目。与 E552（lang-preflight 文档资产污染）分属不同阶段与
根因族。新增价值：给出"老式 I/O 库设备表缓冲区的生命周期判据应使用指针而非
布尔标志"的可复用模式，以及最小 .bas 二分定位法。

## 适用范围与反例

- 适用：所有含"设备表 + 缓冲区指针 + previous/复用标志"结构的 1990s 风格
  stdio 封装层； CLOSE/reopen 生命周期跨平台一致复现；
- 反例：单次打开不复用（previous_buffer 恒 FALSE）不受影响；
- 解除条件：上游修复分配条件后本条转为历史记录。

## 触发实例

bwbasic 2.20pl2（任务 #6153，PR !8575 补丁 0001-bwb_dio.c.patch）：修复后
putget.bas 与全部上游脚本在真机与 CI 同路径执行通过（见 PR test-report.md）。
