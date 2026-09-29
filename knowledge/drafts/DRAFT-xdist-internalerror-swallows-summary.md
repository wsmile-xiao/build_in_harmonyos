# DRAFT — pytest-xdist 在 worker 被信号杀死时抛 INTERNALERROR 并**吞掉整个失败清单**

> 触发事件：psutil 7.2.2 HarmonyOS PC 适配（PR #11263，2026-09-19 真机实测）
> 这是"并行看起来快、实际给出不可信结果"的陷阱：跑得飞快但**失败清单归零**，
> 让人无法逐项归因（也是我一度误判"测试跑通了"的原因之一）。

## 现象

并行跑上游套件时，输出**看似正常结束且很快**，但：

```text
152 failed, 278 passed, 279 skipped, 1 deselected, 1 error in 33.17s
======================= 152 failed, ... =======================
# 然而全文没有任何一行 "FAILED tests/..."
$ grep -c '^FAILED' report.txt
0                # ← 失败清单为空，尽管汇总行说 152 failed
```

同时日志里出现大量 `INTERNALERROR>` 行（实测 41 行）：

```text
[gw4] node down: Not properly terminated
worker 'gw4' crashed while running 'tests/test_sudo.py::TestUpdatedSystemTime::test_boot_time'
...
INTERNALERROR>   File ".../xdist/scheduler/loadscope.py", line 275, in _assign_work_unit
INTERNALERROR>     worker_collection = self.registered_collections[node]
INTERNALERROR> KeyError: <WorkerController gw9>
```

## 根因（实测）

两层叠加：

**① worker 被信号硬杀**（本例为 `test_sudo.py` 的 `time.clock_settime()` 在 OHOS 上
触发 seccomp **SIGSYS(31)**，进程直接被终止——见
`DRAFT-ohos-seccomp-sigsys-clock-settime`）：

```text
$ python3 -c "import time,os; pid=os.fork()
> if pid==0: time.clock_settime(time.CLOCK_REALTIME, time.time())
> _,st=os.waitpid(pid,0); print(os.WTERMSIG(st))"
31               # = SIGSYS，进程被信号杀死而非抛异常
```

**② xdist 调度器无法处理 worker 意外死亡**：worker 消失后其 collection 记录仍在
调度器里，`loadscope` 的 `_assign_work_unit` 访问 `registered_collections[node]`
触发 `KeyError` → 主进程 `pytest_internalerror()` → **在 summary 阶段之前就异常退出**，
于是 `-rf` / short test summary 的 `FAILED` 行**根本没机会打印**。

**关键判据**：汇总行（`N failed`）由 worker 各自上报累计，**即使清单打印环节崩了
也照样输出**——所以"有汇总行 + 无 FAILED 行 + 有 INTERNALERROR"就是本模式。
**不能**据此认为"测试有失败但至少跑完了、能逐项看"。

**旁证：为什么串行能拿到清单**——同一套件、同一构建目录，串行（不带 `-n`）时
`FAILED` 行完好（实测 142 行）。因为串行没有 xdist 调度器，worker 死亡问题不存在
（但那个杀进程的用例仍会中断串行 run，需 `--ignore`）。

## 适用面

任何在以下并行条件下跑上游 pytest 的场景：

- 使用 `pytest-xdist`（`-n N` / `-n auto`）；
- 套件中存在**会让进程被信号杀死**的用例（seccomp SIGSYS、abort、段错误、
  `os._exit`、被 OOM killer 杀、上游 `sys.exit` 于 worker 内等）；
- 需要**逐项失败清单**做归因（PR 描述要求列出失败项及其根因时）——此时并行结果
  不可用。

## 推荐方案

1. **先串行跑一遍取清单**（最高优先级）：串行无调度器、无该崩溃模式，能拿到完整
   可解析的 `FAILED` 行。本例串行全套仅 **59 秒**，成本极低。
2. **把"杀进程"的用例整体排除**：`--ignore=tests/test_sudo.py`（本例），
   从源头消除 worker 死亡；同时排除"挂死"用例
   （`--deselect`，见 `DRAFT-ohos-poll-based-test-infinite-loop`）。
3. **判据写进归因流程**：看到"汇总行 failed>0 但 `^FAILED` 行数为 0"或
   `INTERNALERROR` 出现 ⟹ **该次并行结果不可用于归因**，重跑串行。
4. 若必须并行，可尝试对 worker 死亡更鲁棒的 `--dist worksteal`——但**实测本例
   无效**（仍 `rc=124` 超时），故不应作为首选。

## 禁止做法

- ❌ **不要**把"有汇总行"当作"跑完且可用"：失败清单可能已被吞掉。
- ❌ **不要**在没有 `FAILED` 行的情况下手工编造失败项——无证据即为审计失真（R52）。
- ❌ **不要**靠 `-n auto` 撞大运：本例实测 `-n 8`（无 `--dist loadgroup`）时 8 个
  worker 里只有 1 个真在干活（其余 CPU 时间 0–12 秒），既慢又不可信。
- ❌ **不要**在未排除"杀进程/挂死"用例的前提下反复重跑并行——同一根因，恒同结果。

## 验证证据

- **主证据**：psutil 7.2.2（PR #11263）真机实测，**同一构建目录**对照：

  | 跑法 | 汇总行 | `^FAILED` 行数 | INTERNALERROR | 可用性 |
  |---|---|---|---|---|
  | `-n 8`（无 dist） | 163 failed / 15.6s | **0** | 41 行 | ❌ 清单被吞 |
  | `-n 8 --dist loadgroup` | 152 failed / 33.2s | **0** | 41 行 | ❌ 清单被吞 |
  | `-n 4 --dist loadgroup` | — | **0** | 41 行 | ❌ |
  | `-n 8 --dist worksteal` | rc=124 | 0 | 0 | ❌ 超时 |
  | **串行（排除杀进程/挂死用例）** | 158 failed / **59.6s** | **142** | **0** | ✅ 可归因 |

- **根因证据**：`node down: Not properly terminated` + `worker 'gw4' crashed while
  running 'tests/test_sudo.py::...'`（18 次）+ xdist `loadscope.py:275` 的
  `KeyError: <WorkerController gw9>`；`clock_settime` 子进程 `WTERMSIG=31` 探针。
- **环境**：pytest-xdist 3.8.0 / HarmonyOS PC aarch64 / CPython 3.12。

## 查重结论

- 对 `xdist` 检索全库：**0 命中**（本条为首个记录）。
- 对 `INTERNALERROR` 检索：命中 `DRAFT-ohos-pytest-host-py312-incompat`
  （宿主 python 3.12 与旧版 pytest 的收集器不兼容，属**版本不兼容**导致的收集期
  错误）、以及 3 份以"测试失败清单/债务"为主题的运营类文档——**均未覆盖
  "worker 被信号杀死 → 调度器 KeyError → 失败清单被吞"这一机制**。
- 对 `short test summary` / `失败清单` 检索：无同主题条目。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
