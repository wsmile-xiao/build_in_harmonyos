# DRAFT-E745 — approval/快照测试的 checkout 布局与 git 元数据隐含前提

- 取号：`knowledge_id.py --claim --task snitch-1.2.3` → **E745**（2026-09-25，回查未占用）
- 适用：snitch 1.2.3 及一切 approval/snapshot 快照比对型上游测试
- 状态：UNMATCHED（草稿，待审核提升为 E 条目）

## 一句话

approval/快照测试的**归一化正则把上游 CI 的 checkout 布局写死成字面量**：
tag 归档解包后直接跑，会因「源码路径不含 `/snitch/tests/`」+「版本号少 1 段
（无 .git）」两族前提缺失而整套失配——这是**测量装置问题**，不是产品 bug；
修法是按上游 CI 预期物化源码（目录名 + `git init`），不动 expected 基线、不改上游测试代码。

## 证据链（snitch 1.2.3，三轮对照）

| 轮次 | 源码布局 | approval 结果 | 根因 |
|---|---|---|---|
| attempt1 | `…/builds/snitch-1.2.3.work/tests/` | **0/3 过，734/2782 断言失配** | 归一化正则 `(.+/snitch/tests/)` 不匹配 → 绝对路径逐行失配 |
| attempt2 | `…/native-src/snitch/tests/`（目录名修好） | **1/3 过，11/2782 失配** | 版本归一化要求 4 段 `X.Y.Z.<githash>`（CMake `git log -1`），tag 归档无 .git 只有 3 段 |
| attempt3 | attempt2 + 源码根 `git init && git commit` | **3/3 全过，2782/2782** | 两族前提齐备 |

关键失配原文：
- `expected: message='*testing_reporters.cpp:*|n…'` vs `actual: message='/…/snitch-1.2.3.work/tests/testing_reporters.cpp:171|n…'`
- `expected: catch2-version="*.snitch"` vs `actual: catch2-version="1.2.3.snitch"`
- `expected: starting test with snitch v*` vs `actual: starting test with snitch v1.2.3`

## 判定与处置（详见 .kv 的 rec_approach / solution）

1. 差异全是「实际=绝对路径/3 段版本 vs 期望=`*` 通配」→ 命中本模式。
2. 复刻上游 CI 环境：源码路径满足正则字面量（目录名 `snitch`）+ `git init`
   提供 `git log -1 %h`（hash 值本身被归一化为 `*`，无关紧要）。
3. 重跑判据：approval `test cases: 3 | 3 passed` + `assertions: 2782 | 2782 passed`。
4. 通用化：跑 approval/snapshot 套件前 grep 归一化正则里的
   字面路径段（`REPO/tests`）与版本段数假设；「tag 归档解包即测」对这类套件是高危动作。

## 复现命令

见 .kv 的 `solution` / `verify_cmd`（全部落 `$HOME/tmp/snitch-1.2.3/`，设备可直接执行）。
三轮日志：`$HOME/tmp/snitch-1.2.3/native/`（`*.attempt1.log` / `*.attempt2.log` / 现行 `*.log`）。
