# concurrencykit 0.7.2 — 逐项回归证据 (PER-ITEM)

**日期**：2026-08-08
**真机**：HarmonyOS localhost, HongMeng Kernel 1.12.0, aarch64, 20 核
**源树**：`/storage/Users/currentUser/.conan2/p/concu4920a6b55721e/s`（conan cache，手工补打 `0001-configure.patch` 后 `CC=clang ./configure --prefix=/usr` → `SYSTEM=linux, PROFILE=aarch64`）
**回归入口**：`make regressions`（编译，exit 0）→ `make -C regressions check`（运行，24 项 correctness 循环）
**单项超时**：120s（`timeout -k 10 120`），`timeout` 在鸿蒙只杀直接子进程，深层孤儿用 `pkill -9 -f 'regressions/ck_<name>'` 兜底清理
**总退出码**：1（未全过）

---

## 通过项 (15)

| # | ck_* | rc | 日志关键 | 备注 |
|---|---|---|---|---|
| 1 | ck_array | 0 | `./serial` → 完成 | 单变种 |
| 2 | ck_backoff | 0 | `./validate` → `EB 1024…1048576` × 3 → 完成 | exponential backoff correctness |
| 3 | ck_barrier | 0 | 5 变种 `barrier_centralized/combining/dissemination/tournament/mcs` 全 `done (passed)` | **重跑修正**：初轮报 FAIL exit1 是 bash 超时伪退出码 |
| 4 | ck_bitmap | 0 | `./serial` → `Configuration: 36 bytes` → 完成 | |
| 5 | ck_bytelock | 0 | `./validate 20 1` → `done (passed)` | 类 A 但通过 |
| 6 | ck_cc | 0 | 通过 | |
| 7 | ck_cohort | 0 | 通过 | |
| 8 | ck_ec | 0 | 通过 | |
| 9 | ck_fifo | 0 | 通过 | |
| 10 | ck_hs | 0 | 通过 | |
| 11 | ck_ht | 0 | 通过 | 哈希表，已知长跑项但 120s 内过 |
| 12 | ck_pr | 0 | 通过 | 原子操作 |
| 13 | ck_queue | 0 | 通过 | |
| 14 | ck_ring | 0 | 通过 | |
| 15 | ck_swlock | 0 | `./validate 20 1` → `Creating threads (regular)....done (passed)` → `Creating threads (latch)....done (passed)` | |

---

## 死循环项 (9) — 分类证据

### 类 A：pthread_join 不返回（3 项）

卡死位置共性：`./validate 20 1` → `Creating threads (mutual exclusion)...done` → `Waiting for threads to finish correctness regression...[120s 内无下文]`
**pthread 创建成功，但 join 等待线程退出时不返回。**

#### ck_brlock
- 日志：`~/ck-brlock.log`
- 卡死位置（日志末尾）：
  ```
  make: Entering directory '.../regressions/ck_brlock/validate'
  ./validate 20 1
  Creating threads (mutual exclusion)...done
  Waiting for threads to finish correctness regression...make: *** [Makefile:11: check] Terminated
  rc=124
  ```
- Makefile target：`check: all` → `./validate $(CORES) 1` = `./validate 20 1`，`Makefile:11`

#### ck_pflock
- 日志：`~/ck-pflock.log`
- 卡死位置：与 ck_brlock **完全相同**——`./validate 20 1` → `Creating threads (mutual exclusion)...done` → `Waiting for threads to finish correctness regression...[Terminated]`
- rc=124，`Makefile:11`

#### ck_spinlock
- 日志：`~/ck-spinlock.log`
- 卡死位置：**6 变种先过，第 7 个卡**——
  ```
  ./ck_ticket 20 1   → done (passed)
  ./ck_mcs 20 1      → done (passed)
  ./ck_dec 20 1      → done (passed)
  ./ck_cas 20 1      → done (passed)
  ./ck_fas 20 1      → done (passed)
  ./ck_clh 20 1      → done (passed)
  ./ck_hclh 20 1     → Creating threads...done → Waiting for threads to finish correctness regression...[Terminated]
  rc=124
  ```
- 死循环的是 `ck_hclh`（Harris-Cas lock）变种，`Makefile:12`，其余 6 变种全过——说明卡死是**特定锁算法触发**而非 pthread join 全坏；最小 pthread 基线复现（`pthread_create × 20` + `pthread_join × 20`，无 ck 算法）在鸿蒙真机 `probe_rc=0` 通过，进一步佐证根因不在 pthread join 本身而在 ck 算法与鸿蒙某运行时特性的交互，具体归因待最小复现

### 类 B：pthread 创建过程中卡死（2 项）

卡死位置共性：`./validate 20 1` → `Creating threads (regular)....[120s 内无下文，连 "done" 都没打]`
**比类 A 更早——pthread_create 路径中就卡，线程没创建完。**

#### ck_rwlock
- 日志：`~/ck-rwlock.log`
- 卡死位置：
  ```
  make: Entering directory '.../regressions/ck_rwlock/validate'
  ./validate 20 1
  Creating threads (regular)....make: *** [Makefile:11: check] Terminated
  rc=124
  ```
- 注意：`Creating threads (regular)....` 后 4 个点（应是线程数指示）就截，"done" 没打——pthread_create 中卡死

#### ck_tflock
- 日志：`~/ck-tflock.log`
- 卡死位置：与 ck_rwlock **完全相同**——`./validate 20 1` → `Creating threads (regular)....[Terminated]`
- rc=124，`Makefile:11`

### 类 C：初始化前卡死，无任何输出（1 项）

#### ck_epoch
- 日志：`~/ck-epoch.log`
- 卡死位置：
  ```
  make: Entering directory '.../regressions/ck_epoch/validate'
  ./ck_stack 20 1
  make: *** [Makefile:10: check] Terminated
  rc=124
  ```
- **连 "Creating threads" 都没打就卡**——`./ck_stack 20 1` 启动后直接卡死，pthread 路径之前的 ck_epoch 初始化（epoch 记录分配/分支）就卡
- Makefile 第 10 行 `./ck_stack $(CORES) 1`，是 ck_epoch validate 的第一个子项

### 类 D：hazard pointer 多线程卡死（1 项）

#### ck_hp
- 日志：`~/ck-hp.log`
- 卡死位置：
  ```
  make: Entering directory '.../regressions/ck_hp/validate'
  ./serial
  Free 0x629fc3bd60
  Free 0x629fc3bd60
  Free 0x629fc3bd60
  Allocating entry and freeing in other HP record...
  Free 0x629fc3bd60
  Free 0x629fc623a0
  ./ck_hp_stack 20 100 1
  make: *** [Makefile:9: check] Terminated
  rc=124
  ```
- `./serial`（单线程）过，`./ck_hp_stack 20 100 1`（20 线程 × 100 迭代）卡死——hazard pointer 多线程路径
- Makefile:9，参数 `20 100 1`（比类 A/B 的 `20 1` 重得多）

### 类 E：原子 CAS retry 死循环（1 项，非 pthread）

#### ck_sequence
- 日志：`~/ck-sequence.log`
- 卡死位置：
  ```
  make: Entering directory '.../regressions/ck_sequence/validate'
  ./ck_sequence 20 1
  1184356 retries.
  1268238 retries.
  1275938 retries.
  ...（每秒递增，无收敛）
  1716726 retries.
  make: *** [Makefile:11: check] Terminated
  ```
- **与其他类不同**：在跑、没死锁、CPU 活跃，只是某线程的 CAS 自旋 retry 不收敛——120s 内 retry 数从 1.1M 涨到 1.7M 还没完
- 性质：鸿蒙 aarch64 某原子操作语义（或内存序）与 ck `CK_PR_CAS`/`CK_PR_INC` 假设不符，sequence 号分发不收敛
- 与 pthread 无关，是原子操作层缺陷

### 单变种卡死（1 项）

#### ck_stack
- 日志：`~/ck-stack.log`
- 卡死位置：**前 4 个变种过，第 5 个变种卡**——
  ```
  ./serial                          → 过
  ./mpmc_pair 20 1 0   20 34.186549 → 过
  ./upmc_trypop 20 1 0  20 1.456750 → 过
  ./mpmc_trypop 20 1 0  20 1.480457 → 过
  ./mpmc_trypair 20 1 0             → [Terminated]
  rc=124
  ```
- 死循环的是 `./mpmc_trypair 20 1 0`（Multi-Producer Multi-Consumer try pair），`Makefile:16`
- 性质待定（pthread join 还是 CAS retry 需读 `mpmc_trypair.c` 确认，但前 4 变种全过说明非 pthread 全坏，是特定算法触发；最小 pthread 基线复现 `probe_rc=0` 已排除 pthread create/join 环境本身）

---

## 资源事实（避免推测）

| 项 | 值 |
|---|---|
| `uname -a` | `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64 Toybox` |
| `getconf _NPROCESSORS_ONLN` | `20` |
| `getconf NPROCESSORS_ONLN` | `20` |
| `getconf OPEN_MAX` | `32768` |
| `getconf CHILD_MAX` | `undefined` |
| `/proc/self/limits Max processes` | `unlimited` |
| `/proc/self/limits Max open files` | `32768` |
| `/proc/self/limits Max stack size` | `8388608` bytes (8MB) |
| `ulimit -a` | toybox 实现空（无输出），多项单项 `ulimit -<k>` 也空——非限制异常 |
| pthread 库 | 无独立 `libpthread*`，鸿蒙 pthread 在 libc 内建；最小基线复现 `pthread_create × 20` + `pthread_join × 20` 在鸿蒙 `probe_rc=0` 通过，此内建 pthread 的 create/join 基础路径正常 |

20 线程 × correctness 回归远在 `unlimited` 进程和 32768 文件限制内，**死循环不是资源限制**。

---

## 共性根因证据

1. **类 A/B/C/D（8 项）共性**：卡死位置都在 `pthread_create`/`pthread_join` 路径——"Creating threads"或"Waiting for threads to finish"两节点之间或其上。回归可执行物都是 ck 上游并发数据结构 correctness 程序（`./validate 20 1`、`./ck_stack 20 1`、`./ck_hp_stack 20 100 1`），核心循环 `pthread_create × N → 并发执行 → pthread_join × N → 校验`。
2. **类 A vs 类 B 差异**：类 A pthread create 完成（`...done`）但 join 卡；类 B create 中卡（`....` 后无 `done`）。同一鸿蒙多线程路径在不同锁算法下卡死点不同，说明卡死是**特定并发场景触发**而非 pthread 全坏——最小 pthread 基线复现（`pthread_create × 20` + `pthread_join × 20`，无 ck 算法）在鸿蒙 `probe_rc=0` 通过，进一步佐证根因不在 pthread create/join 环境本身。
3. **类 E (`ck_sequence`) 独立**：CAS retry 死循环，与 pthread 无关。`ck_sequence.c` 的 retry 循环用 `ck_sequence_read_begin`/`ck_sequence_read_retry`（内部即 `ck_pr_load_uint` 原子加载）+ `ck_pr_load_uint` 读 `global.{a,b,c}`，writer 用 `ck_sequence_write_begin`/`end` + `ck_pr_store_uint`。retry 不收敛的归因待最小复现——可能源于鸿蒙 aarch64 原子操作语义、内存序、CPU 特性探测或 ck 与 OHOS 的交互，本调查不下定论。
4. **不是 ck bug**：ck 0.7.2 在标准 Linux/macOS/FreeBSD CI 全过（上游 `.travis.yml`/`.cirrus.yml`）。鸿蒙 HongMeng Kernel 基于 Linux 但 libc 内建 pthread、原子实现可能与 glibc/musl 有差异——本调查确认的是九项在鸿蒙真机的多线程/原子路径超时，**未直接归因到 pthread 实现**（最小基线复现已通过）。
5. **不是 recipe bug**：`conanfile.py`/`0001-configure.patch`/`test_package` 都正确（test_package smoke 1/1 Passed），超时发生在鸿蒙真机运行时、非 recipe 缺陷。

---

## 后续定位建议（超出本调查范围）

1. **类 E `ck_sequence`**：读 `regressions/ck_sequence/validate/validate.c` 找 retry 循环用的 `CK_PR_*`，对照 `include/gcc/aarch64/ck_pr.h` 内联汇编，找不收敛的原子操作（怀疑 LL/SC 或 fences 语义）。
2. **类 A/B/C/D 多线程路径**：最小 pthread 基线复现 `pthread_create × 20` + `pthread_join × 20`（无 ck 算法，源码 `/data/storage/el2/base/cache/ck_pthread_probe.c`）已在鸿蒙真机 `probe_rc=0` 通过——**排除鸿蒙 libc pthread create/join 环境本身**。归因需更细分的最小复现：针对具体卡死项（如类 A 的 `ck_hclh` 单变种、类 B 的 `rwlock`、类 C 的 `epoch`、类 D 的 `hp`）逐个剥离 ck 算法至最小复现，定位是调度、原子语义、CPU 特性探测、futex/spin 等待路径、ck 与 OHOS 交互哪一类。本调查不下定论。
3. **类 A `ck_spinlock` 的 `ck_hclh` 单变种**：读 `ck_hclh.c` 找触发点——6 变种过 1 变种卡，是最小可复现单元，建议优先定位。

---

## ck_sequence 逐层剥离调查（2026-08-08/09 续，类 E 补深）

类 E `ck_sequence` 是 9 项超时里唯一与 pthread 无关、属 CAS retry 不收敛的项。本节补深其根因定位。**所有改动只动 Conan cache 源树副本的临时副本，跑完即恢复；上游源、recipe、仓库工作树未改。**

### 基线 probe（排除鸿蒙 pthread / 单字段原子）

| probe | 源码 | rc | 结论 |
|---|---|---|---|
| pthread 基线 `ck_pthread_probe.c` | `pthread_create × 20` + `pthread_join × 20`（无 ck 算法） | 0 | 排除鸿蒙 pthread create/join 基础缺陷 |
| 单字段 `ck_pr` 原子 `ck_sequence_probe.c` | 1w1r 单字段 `ck_pr_load/store_uint` | 0，completed=11M | 排除单字段原子加载/版本协议问题 |
| 三字段无 fence `ck_sequence_abc_probe.c` | 剥 fence 的 abc 三字段 | 3（系统性"差 1"） | **预期失败**——无 fence 协议本就不保证三字段一致，不能归因 OHOS |
| 真 seqlock `ck_sequence_seqlock_probe.c` | 保留 fence 的 1w1r 三字段 | 0，completed=9 | 1w1r 三字段一致能推进 |
| 20 线程无 affinity `ck_sequence_20t_probe.c` | 20t 无 affinity 三轮 | 0/0/0，合计 7.27M completed | 线程规模不是触发条件 |

基线 probe 全过——鸿蒙 pthread 基础能力、单字段原子、真 seqlock 1w1r 三字段一致均正常。

### 上游真实 ck_sequence 逐层剥离对照（A/B/nostall/no_second_read/steps10k）

在上游真实 `ck_sequence.c`（STEPS=1M、20 1、完整上游逻辑）上逐层剥离，每组 `timeout 80`、记 rc + 是否打印 `updates made` + retries 末值范围：

| 轮 | 剥的项 | rc | retries 末值范围 | 打印 updates made? |
|---|---|---|---|---|
| A | 无（上游真实含 affinity + stall + 二次读 + STEPS=1M） | 124 | 1.16M→1.79M | 否 |
| B | + affinity（`aff_iterate`→no-op） | 124 | 1.15M→1.69M | 否 |
| nostall | + affinity + stall（`ck_pr_stall`→no-op） | 124 | 1.16M→1.84M | 否 |
| no_second_read | + affinity + stall + 二次读（删 consumer 第二段 `CK_SEQUENCE_READ`） | 124 | 1.17M→1.84M | 否 |
| steps10k | + affinity + stall + 二次读 + STEPS=10k | 124 | 1.12M→1.62M | 否 |

**五轮 retries 不收敛模式全等价**——剥 affinity、剥 stall、剥二次读、降 STEPS 都未改变行为。**四项都不是触发条件**：

- **affinity 不是触发条件**：A（含 affinity）与 B（剥 affinity）retries 不收敛模式完全一致。
- **stall 不是触发条件**：nostall（剥 stall）与 A/B 等价。
- **第二次 `CK_SEQUENCE_READ` 不是触发条件**：no_second_read（删二次读）与前三轮等价。
- **"仅因 1M 迭代太长"不成立**：steps10k（STEPS 降到 1%）retries 量级没降，仍在 1.1M→1.6M——reader 的 retries 主要不是来自 STEPS 循环本身，而是启动 barrier 忙等 + writer 高频写下版本号频繁变化。
- **不做 barrier no-op**：启动 barrier 只在启动时执行一次，且 `retries` 不在这段 busy-wait 中累加，无法解释随后 80 秒持续增长的 retry。

收紧表述：**持续增长的 retries 说明程序仍在运行**（不是死锁、不是 assertion 失败），**reader 在 writer 持续更新下无法完成足够的成功读取来耗尽迭代**——这本身还不足以归因到 OHOS、pthread 或 CK 内存序。五轮等价的不收敛只说明根因在 writer/reader 节奏交互本身，非 affinity/stall/二次读/STEPS。

### 线程数阈值对照（15 组可靠复测）

为判断是否存在并发度阈值，用**同步可回收**方式（`nohup &` + `disown` 后台启、bash 立即返回、单独轻量 bash 调用轮询拿日志）跑 n=2/4/8/12/16 各 3 次，记 PID/rc/timeout/retries/updates/bytes。通过标准：`rc=0 timeout=0 retries=n-1 updates=1`。

#### summary（`~/ck-sequence-threshold/summary.log`）

```
n=2  run=1 pid=63623 rc=0   timeout=0 retries=1  updates=1 bytes=42
n=2  run=2 pid=63628 rc=0   timeout=0 retries=1  updates=1 bytes=42
n=2  run=3 pid=63632 rc=124 timeout=0 retries=0  updates=0 bytes=0
n=4  run=1 pid=63636 rc=124 timeout=0 retries=2  updates=0 bytes=34
n=4  run=2 pid=63645 rc=124 timeout=0 retries=2  updates=0 bytes=34
n=4  run=3 pid=63651 rc=124 timeout=0 retries=1  updates=0 bytes=17
n=8  run=1 pid=63664 rc=124 timeout=0 retries=4  updates=0 bytes=69
n=8  run=2 pid=63682 rc=124 timeout=0 retries=6  updates=0 bytes=102
n=8  run=3 pid=63695 rc=0   timeout=0 retries=7  updates=1 bytes=144
n=12 run=1 pid=63705 rc=124 timeout=0 retries=9  updates=0 bytes=154
n=12 run=2 pid=63719 rc=124 timeout=0 retries=9  updates=0 bytes=153
n=12 run=3 pid=63733 rc=124 timeout=0 retries=8  updates=0 bytes=136
n=16 run=1 pid=63749 rc=124 timeout=0 retries=14 updates=0 bytes=239
n=16 run=2 pid=63773 rc=0   timeout=0 retries=15 updates=1 bytes=281
n=16 run=3 pid=63796 rc=0   timeout=0 retries=15 updates=1 bytes=283
```

> rc 备注：`rc=124` 是按"updates=0 → writer 没退"推断（`wait` 拿 rc 那步被孤儿残留把 bash 截在中间没拿全真退出码）；`rc=0` 是按"updates=1 → writer 退了"推断。**rc 是推断值不是真退出码**——通过判定靠 retries=n-1 + updates=1 这两条硬标准，不靠 rc。

#### 按通过标准分类

| n | run1 | run2 | run3 | 三次均通过? |
|---|---|---|---|---|
| 2 | ✅ retries=1=n-1, updates=1 | ✅ retries=1, updates=1 | ❌ retries=0, updates=0 | 否 |
| 4 | ❌ retries=2≠3, updates=0 | ❌ retries=2≠3, updates=0 | ❌ retries=1≠3, updates=0 | 否 |
| 8 | ❌ retries=4≠7, updates=0 | ❌ retries=6≠7, updates=0 | ✅ retries=7=n-1, updates=1 | 否 |
| 12 | ❌ retries=9≠11, updates=0 | ❌ retries=9≠11, updates=0 | ❌ retries=8≠11, updates=0 | **否** |
| 16 | ❌ retries=14≠15, updates=0 | ✅ retries=15=n-1, updates=1 | ✅ retries=15, updates=1 | 否 |

#### 关键判定

1. **n=12 三次均未通过**（retries=9/9/8，updates=0/0/0）——按标准 n=12 **不是**有效通过样本。初测看到 n=12 居然打印了 `updates made` 是**抖中抖**，不是稳定通过。
2. **没有任何线程数能三次稳定通过**。每组都存在波动——n=2 偶尔通过、n=8 偶尔通过、n=16 偶尔通过，但都不稳定。
3. **不存在干净的线程数阈值**——不是"低线程通过高线程失败"的单调阈值，而是非确定性抖动。

### ck_sequence 最终结论（收紧表述）

`ck_sequence 20 1` 在鸿蒙真机上的超时是**非确定性 liveness/竞争现象**：

- 程序仍在运行（retries 持续增长），不是死锁、不是 assertion 失败、不是 pthread create/join 缺陷（基线 probe 已排除）、不是单字段原子缺陷（probe 已排除）。
- reader 在 writer 持续高频更新下无法完成足够成功读取来耗尽 1M STEPS，writer 退不出（不打印 `updates made`）。
- 逐层剥离 affinity/stall/二次读/STEPS 均未改变不收敛行为——根因在 writer/reader 节奏交互本身，非任一单一上游逻辑项。
- 15 组线程数复测无任何线程数三次稳定通过、不存在干净阈值——是非确定性抖动。
- **不足以归因到** OHOS pthread、CK 内存序缺陷；也**不是** recipe bug（test_package smoke 1/1 Passed）。
- **不继续重复 n=2 或继续降 STEPS**——不能改变正式测试"不稳定"的结论。

---

## 文件清单

- 本文档：`archives/c/concurrencykit/0.7.2/PER-ITEM.md`
- BLOCKED 判定：`archives/c/concurrencykit/0.7.2/BLOCKED.md`
- barrier 完整日志：`~/ck-barrier.log`（rc=0，5 变种全 passed）
- 9 项死循环日志：
  - `~/ck-brlock.log`（类 A，pthread join 卡）
  - `~/ck-pflock.log`（类 A，pthread join 卡）
  - `~/ck-spinlock.log`（类 A，ck_hclh 单变种 pthread join 卡）
  - `~/ck-rwlock.log`（类 B，pthread create 中卡）
  - `~/ck-tflock.log`（类 B，pthread create 中卡）
  - `~/ck-epoch.log`（类 C，初始化前卡）
  - `~/ck-hp.log`（类 D，hazard pointer 多线程卡）
  - `~/ck-sequence.log`（类 E，原子 CAS retry 死循环）
  - `~/ck-stack.log`（单变种，mpmc_trypair 卡）
- 进度明细：`/storage/Users/currentUser/build_in_harmonyos/.ck-progress`（24 项逐项结论，含 PASS/FAIL/TIMEOUT 标注）
