# 墙钟性能阈值被写成断言 → 设备边界上 Passed/Failed 抖动（E708 草稿）

> 状态：草稿（DRAFT，待人工审核）｜来源：paraglob 0.6.0 OHOS aarch64 适配（2026-09-24）｜severity: 3

## 问题

修完测量装置（E706）后，btest 套件 3/4 通过，唯一失败：

```
driver.time ... failed
  % 'btest-diff out' failed unexpectedly (exit code 1)
  == Diff ==
  -Passed.
  +Failed.
```

同一 HEAD 连跑：`Passed. / Failed. / Passed. / Failed. / Passed.`——**结果不可复现**。

## 根因

`tools/driver.cpp` 把性能当正确性断言：

```cpp
double elapsed = benchmark(a, b, c, max_time);
if (max_time > 0) {
    if (elapsed <= max_time) std::cout << "Passed.\n";
    else                     std::cout << "Failed.\n";
}
```

`elapsed` = 建图 + 查询总耗时，阈值 3s（`paraglob-test -b 10000 20000 10 3`）。
`tools/benchmark.cpp` 用 `std::random_device` 播种 `std::mt19937`，每次工作负载
都不同 → **阈值附近的耗时会在两侧跳**。

实测（aarch64 / clang 15 / `-O3` / Release，证据 `$HOME/tmp/paraglob-0.6.0/w0/`）：

| 形态 | 读数 |
|---|---|
| 明细 `-b 10000 20000 10 0` ×3 | build 1.655/1.707/1.770 s + search 1.287/1.321/1.413 s = **3.028/3.057/3.068 s** vs 阈值 3.0 s |
| 判定 `-b 10000 20000 10 3` ×20 | `Passed.` **2/20**、`Failed.` 18/20（wall 3.467–3.870 s） |
| 规模对照 `-b 1000 2000 10 3` ×5 | **5/5 `Passed.`** |
| 同规模功能明细 | Build 0.120 s、Search 0.017 s、**114648 queries/s** |

`grep -c "assert("` 源码 = **0** ⇒ 与 NDEBUG / 编译旗标无关，排除死胡同方向。

## 处置（attribute，不 mask）

1. **拆明细**：无阈值形态取 Build/Search 分项，看与阈值的相对量级（差 1% vs
   差一个数量级——本例是 0.9%–2.3%，典型的「骑边界」）。
2. **取样本**：判定形态连跑 20 次，区分「稳定失败」与「抖动」。
3. **规模对照**：同代码路径缩规模 5/5 通过 + 吞吐正常 ⇒ 排除功能/适配问题。
4. **如实进四分项**：`TOTAL=4 = PASS 3 + FAIL 1 + SKIP 0 + NOT_RUN 0`，
   该例**计 FAIL**，并在 notes / test-report 非 PASS 段 / PR 正文写明
   「环境性能限制 + 替代验证」。

> **不许把归因清晰的用例剔出 N**——N 少报是 rule4 硬 FAIL（近段 20 份外部审查
> 命中 5 次）；归因只改变「怎么解释」，不改变「计不计数」。

## 禁止的做法

1. `btest -U/-u` 把 `Failed.` 回填成基线 = 篡改上游预期。
2. 把 `driver.time` 从 N 里剔除或计 SKIP（无据跳过）。
3. 往 `-DNDEBUG`/优化级别方向反复调参（源码 0 处 `assert(`，已实测排除）。

## 复现命令（设备可直接执行）

```sh
. "$HOME/tmp/paraglob-0.6.0/env.sh"
BIN="$HOME/ws/tmp/test-install-paraglob-0.6.0/bin/paraglob-test"
"$BIN" -b 10000 20000 10 0        # Build/Search 分项
for i in 1 2 3 4 5; do "$BIN" -b 10000 20000 10 3; done
"$BIN" -b 1000 2000 10 3          # 规模对照
```

完整样本脚本：`$HOME/tmp/paraglob-0.6.0/w0/bench_probe.py`
（输出 `$HOME/tmp/paraglob-0.6.0/w0/bench-probe.body.md`）。

## 关联

- 前置：E706（`btest-diff` 硬编码 `/tmp`，装置未修时读数不可采信——**先修装置再读数**）。
- 同族：`notes/device-facts.md` §二.20（计数口径与 N 少报红线）。
