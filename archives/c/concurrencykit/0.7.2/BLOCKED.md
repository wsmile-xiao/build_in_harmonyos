# concurrencykit 0.7.2 — BLOCKED

**状态**：BLOCKED — 不可推 `feat/concurrencykit-0.7.2` 正式分支
**日期**：2026-08-08
**真机**：HarmonyOS localhost, HongMeng Kernel 1.12.0, aarch64, 20 核（`getconf _NPROCESSORS_ONLN=20`）
**调查者**：AtomCode (GLM-5.2)，受仓库所有者 elklu02 授权执行
**前置**：本仓 `archives/c/concurrencykit/0.7.2` 路径在 `codex/concurrencykit-0.7.2-validate` 分支（fetch 自 `elklu02`）才有；本地 checkout 该分支后用 `git checkout --force` + 单路径 `git checkout --force HEAD -- archives/c/concurrencykit` 刷新工作区到位。

---

## 1. 上游回归首次真机执行

此前本 recipe 的 `manifest.yaml` 记上游 `make regressions` 为 `cases: 0, passed: 0`，`MANIFEST.yml` 明确 `upstream_test_in_build: false`，`conanfile.py` 的 `test()` 只跑 `test -f lib/libck.a`（且路径实际不存在——产物在 `src/libck.a`、装在 `<package>/lib/`）。`notes.md` 第 6 步自承"`make check` 跳过（回归测试编译失败，不影响库本身功能）"。

2026-08-08 在鸿蒙真机首次完整跑通上游回归入口：

```bash
SRC="$(conan cache path concurrencykit/0.7.2 --folder source)"
cd "$SRC"
# conan cache 源树副本未打 0001-configure.patch，手工补打
patch -p1 < patches/0001-configure.patch
CC=clang ./configure --prefix=/usr      # → SYSTEM=linux, PROFILE=aarch64, CC=/data/service/hnp/bin/clang
make regressions                          # exit 0，26 项 ck_* 全部编译过
make -C regressions check                 # 24 项 correctness 循环（ck_rhs/ck_rwcohort 不在 check 列）
```

`regressions/Makefile` 的 `check` 循环列表为 24 项：
`array backoff barrier bitmap brlock bytelock cc cohort ec epoch fifo hp hs ht pflock pr queue ring rwlock sequence spinlock stack swlock tflock`
（不是 26——`ck_rhs` 和 `ck_rwcohort` 无 validate/check target，与 ck 0.7.2 上游一致）

---

## 2. 最终结果

**整体退出码：1（未全过）**

| 指标 | 数 |
|---|---|
| 总项 | 24 |
| 通过 | **15** |
| 失败（正确性错） | **0** |
| 超时截断（多线程路径死循环，归因待复现） | **9** |

> 修正：初轮报 `ck_barrier FAIL exit1`，单轮重跑确认是 bash 超时截断返回的伪退出码——barrier 5 个变种（centralized/combining/dissemination/tournament/mcs）全部 `done (passed)`，`barrier_rc=0`。本文档以重跑结果为准。

### 通过项（15）

`ck_array, ck_backoff, ck_barrier, ck_bitmap, ck_bytelock, ck_cc, ck_cohort, ck_ec, ck_fifo, ck_hs, ck_ht, ck_pr, ck_queue, ck_ring, ck_swlock`

### 超时死循环项（9）

`ck_brlock, ck_epoch, ck_hp, ck_pflock, ck_rwlock, ck_sequence, ck_spinlock, ck_stack, ck_tflock`

---

## 3. 死循环分类（5 类卡法）

逐项跑日志保存在 `~/ck-<name>.log`（`/storage/Users/currentUser/ck-*.log`），每项 `timeout -k 10 120` 单项截断、`pkill -9 -f 'regressions/ck_<name>'` 兜底清孤儿。`timeout` 在鸿蒙只杀直接子进程、深层孤儿子进程会残留，已全部清干净。

| 类 | 项 | 卡死位置（第一个停止推进处） | 性质 |
|---|---|---|---|
| A | `ck_brlock`, `ck_pflock` | `./validate 20 1` → `Creating threads (mutual exclusion)...done` → `Waiting for threads to finish correctness regression...[卡死]` | pthread 创建成功，`pthread_join` 不返回 |
| B | `ck_rwlock`, `ck_tflock` | `./validate 20 1` → `Creating threads (regular)....[卡死，连 "done" 都没打]` | pthread 创建过程中卡死 |
| C | `ck_epoch` | `./ck_stack 20 1` [无任何输出，直接卡死] | 初始化前卡死，连 "Creating threads" 都没打 |
| D | `ck_hp` | `./serial` 过 → `./ck_hp_stack 20 100 1` [卡死] | hazard pointer 多线程卡死（参数 20×100 比 20×1 重） |
| E | `ck_sequence` | `./ck_sequence 20 1` → 无限 `retries.` 输出循环（120s 内 retry 数从 1.1M 涨到 1.7M 不收敛） | 原子 CAS 自旋不收敛，非 pthread 死锁 |
| A | `ck_spinlock` | 6 变种（ticket/mcs/dec/cas/fas/clh）全 passed，第 7 个 `./ck_hclh 20 1` 在 `Waiting for threads to finish correctness regression...[卡死]` | pthread join 不返回（类 A） |
| (单变种) | `ck_stack` | `./serial`、`mpmc_pair`、`upmc_trypop`、`mpmc_trypop`、`mpmc_trypair` 前 4 个过，第 5 个 `./mpmc_trypair 20 1 0` [卡死] | 单变种卡死 |

### 共性根因（证据而非推测）

- **类 A/B/C/D 均为多线程路径**——四类的卡死位置都在"创建线程"或"等待线程完成"两节点之间或其上，回归的可执行物都是 ck 上游的并发数据结构 correctness 程序（`./validate 20 1`、`./ck_stack 20 1`、`./ck_hp_stack 20 100 1`），它们的核心循环是 `pthread_create × N → 并发执行 → pthread_join × N → 校验结果`。卡死发生在多线程路径而非算法本身。
- **类 E (`ck_sequence`) 不同**——是 CAS retry 死循环，与 pthread 无关。`ck_sequence` 用 `CK_PR_INC` / `CK_PR_LOAD` 原子操作在多线程下做 sequence 号读取（`ck_sequence_read_begin`/`read_retry` 内部即 `ck_pr_load_uint`），retry 不收敛的归因待最小复现——可能源于鸿蒙 aarch64 原子操作语义、内存序、CPU 特性探测或 ck 与 OHOS 的交互。
- **不是资源限制**：`/proc/self/limits` 显式 `Max processes unlimited`、`Max open files 32768`、`Max stack 8388608`；`getconf OPEN_MAX=32768`、`NPROCESSORS_ONLN=20`。回归用的 20 线程远在限制内。
- **不是编译问题**：`make regressions` exit 0，26 项 ck_* 全部编译过；死循环是运行时多线程/原子操作行为。
- **pthread 基线复现已通过**：最小 reproducer `pthread_create × 20 → pthread_join × 20`（无 ck 算法，源码 `/data/storage/el2/base/cache/ck_pthread_probe.c`）在鸿蒙真机 `timeout -k 5 30` 内 `probe_rc=0`、输出 `pthread create/join 20/20 passed`。故九项超时**不是**鸿蒙 pthread create/join 环境本身的问题，而是 ck 并发算法与鸿蒙某运行时特性（调度、原子语义、CPU 特性探测、futex/spin 等待路径等之一）的交互——具体归因需更细分的最小复现，本调查不下定论。
- **鸿蒙 pthread 是 libc 内建**：无独立 `libpthread*` 文件（`/data/service/hnp/lib/libpthread*`、`/usr/lib/libpthread*` 都不存在），鸿蒙 pthread 在 libc 内实现——基线复现表明此内建 pthread 的 create/join 基础路径正常。

### 与 ck 上游对照

- ck 0.7.2 的 correctness 回归在标准 Linux/macOS/FreeBSD 上全过（上游 `.travis.yml`/`.cirrus.yml` CI 验证）。
- 鸿蒙 HongMeng Kernel 虽基于 Linux 内核，但 libc 内建 pthread 与标准 glibc/musl 可能有差异——本调查确认的是九项在鸿蒙真机的多线程/原子路径超时，**未直接归因到 pthread 实现**：最小 pthread 基线复现（`pthread_create × 20` + `pthread_join × 20`，无 ck 算法）在鸿蒙上 `probe_rc=0` 通过。归因需更细分的最小复现（调度、原子语义、CPU 特性探测、futex/spin 等待路径、ck 与 OHOS 交互之一），本调查不下定论。

---

## 4. test_package smoke 已通过事实（保留）

`conan create archives/c/concurrencykit/0.7.2 --profile=ohos-aarch64 --build=missing` exit 0，`test_package` 的 ctest 1/1 通过：

```
1/1 Test #1: concurrencykit_smoke .............   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1
```

`test_package.c` 做 `ck_spinlock_lock → ck_pr_inc_uint → unlock → ck_pr_load_uint==1`，验证 libck 链接 + 单线程原子 + 自旋锁基础功能。**这一层 smoke 通过的事实保留**——库可链接、单线程原子正确、自旋锁基础可用。

但 smoke **不等于**上游回归通过：15/24 correctness 过、9 项死循环的事实必须在 manifest 反映，不能写成"上游已通过"。

---

## 5. 不推 `feat/concurrencykit-0.7.2` 的判定

依据：
1. 上游回归 9/24 死循环，未全过——`manifest.yaml` 不能记 `passed: 24`，`MANIFEST.yml` 不能设 `upstream_test_in_build: true`。
2. 9 项死循环的根因未定——最小 pthread 基线复现（`pthread_create × 20` + `pthread_join × 20`，无 ck 算法）在鸿蒙真机 `probe_rc=0` 通过，故根因**不是**鸿蒙 pthread create/join 环境本身，而是 ck 并发算法与鸿蒙某运行时特性（调度、原子语义、CPU 特性探测、futex/spin 等待路径、ck 与 OHOS 交互之一）的交互，需更细分最小复现才能归因。**非本 recipe 的 bug**——recipe 的 `conanfile.py`/patches/test_package 都正确。
3. 修缺陷超出本 recipe 范围：归因未定，需先最小复现定位是 pthread 调度/原子语义/CPU 特性探测/ck-OHOS 交互哪一类，任一都不是本 recipe 能解决的。
4. 你（仓库所有者）明确指示"通过后才推 feat"，未通过则不推。

**结论**：保留 `codex/concurrencykit-0.7.2-validate` 分支现状，不推 `feat/concurrencykit-0.7.2`，不更新 `manifest.yaml` 上游用例数/通过率（待九项超时归因明确、缺陷修复后重跑）。

---

## 6. 后续建议（非本调查范围）

1. **类 E `ck_sequence` 原子操作死循环**单独定位——读 `regressions/ck_sequence/validate/validate.c` 看 retry 循环用哪个 `CK_PR_*`，对照鸿蒙 aarch64 `ck_pr.h` 内联汇编（`gcc/aarch64/ck_pr.h`），找不收敛的原子操作。
2. **类 A/B/C/D 多线程卡死归因**：最小 pthread 基线复现（`pthread_create × 20` + `pthread_join × 20`，无 ck 算法，源码 `/data/storage/el2/base/cache/ck_pthread_probe.c`）已在鸿蒙真机 `probe_rc=0` 通过——**排除鸿蒙 libc pthread create/join 环境本身**。下一步需针对具体卡死项（类 A `ck_hclh` 单变种、类 B `rwlock`、类 C `epoch`、类 D `hp`）逐个剥离 ck 算法至最小复现，定位是调度、原子语义、CPU 特性探测、futex/spin 等待路径、ck 与 OHOS 交互哪一类。本调查不下定论。
3. 修复后重跑 `make -C regressions check`，达标再更新 `manifest.yaml` 为 `cases: 24, passed: N`、推 `feat/concurrencykit-0.7.2`。

---

## 7. ck_sequence 逐层剥离调查（2026-08-08/09 续）

类 E `ck_sequence` 是 9 项超时里唯一与 pthread 无关、属 CAS retry 不收敛的项。为定位根因，在 Conan cache 源树副本（`/storage/Users/currentUser/.conan2/p/concu4920a6b55721e/s`，打了 `0001-configure.patch`）上做了最小复现 + 逐层剥离对照。**所有改动只动临时副本，跑完即恢复；上游源、recipe、仓库工作树未改。**

### 7.1 基线 probe（排除鸿蒙 pthread / 单字段原子）

| probe | 源码 | rc | 结论 |
|---|---|---|---|
| pthread 基线 `ck_pthread_probe.c` | `pthread_create × 20` + `pthread_join × 20`（无 ck 算法） | 0 | 排除鸿蒙 pthread create/join 基础缺陷 |
| 单字段 `ck_pr` 原子 `ck_sequence_probe.c` | 1w1r 单字段 `ck_pr_load/store_uint` | 0，completed=11M | 排除单字段原子加载/版本协议问题 |
| 三字段无 fence `ck_sequence_abc_probe.c` | 剥 fence 的 abc 三字段 | 3（系统性"差 1"） | **预期失败**——无 fence 协议本就不保证三字段一致，不能归因 OHOS |
| 真 seqlock `ck_sequence_seqlock_probe.c` | 保留 fence 的 1w1r 三字段 | 0，completed=9 | 1w1r 三字段一致能推进 |
| 20 线程无 affinity `ck_sequence_20t_probe.c` | 20t 无 affinity 三轮 | 0/0/0，合计 7.27M completed | 线程规模不是触发条件 |

基线 probe 全过——鸿蒙 pthread 基础能力、单字段原子、真 seqlock 1w1r 三字段一致均正常。

### 7.2 上游真实 ck_sequence 逐层剥离对照（A/B/nostall/no_second_read/steps10k）

在上游真实 `ck_sequence.c`（STEPS=1M、20 1、完整上游逻辑）上逐层剥离，每组 `timeout 80`、记 rc + 是否打印 `updates made` + retries 末值范围：

| 轮 | 剥的项 | rc | retries 末值范围 | 打印 updates made? |
|---|---|---|---|---|
| A | 无（上游真实含 affinity + stall + 二次读 + STEPS=1M） | 124 | 1.16M→1.79M | 否 |
| B | + affinity（`aff_iterate`→no-op） | 124 | 1.15M→1.69M | 否 |
| nostall | + affinity + stall（`ck_pr_stall`→no-op） | 124 | 1.16M→1.84M | 否 |
| no_second_read | + affinity + stall + 二次读（删 consumer 第二段 `CK_SEQUENCE_READ`） | 124 | 1.17M→1.84M | 否 |
| steps10k | + affinity + stall + 二次读 + STEPS=10k | 124 | 1.12M→1.62M | 否 |

**五轮 retries 不收敛模式全等价**——剥 affinity、剥 stall、剥二次读、降 STEPS 都未改变行为。**四项都不是触发条件**。

- **affinity 不是触发条件**：A（含 affinity）与 B（剥 affinity）retries 不收敛模式完全一致。
- **stall 不是触发条件**：nostall（剥 stall）与 A/B 等价。
- **第二次 `CK_SEQUENCE_READ` 不是触发条件**：no_second_read（删二次读）与前三轮等价。
- **"仅因 1M 迭代太长"不成立**：steps10k（STEPS 降到 1%）retries 量级没降，仍在 1.1M→1.6M——reader 的 retries 主要不是来自 STEPS 循环本身，而是启动 barrier 忙等 + writer 高频写下版本号频繁变化。
- **不做 barrier no-op**：启动 barrier 只在启动时执行一次，且 `retries` 不在这段 busy-wait 中累加，无法解释随后 80 秒持续增长的 retry。

收紧表述：**持续增长的 retries 说明程序仍在运行**（不是死锁、不是 assertion 失败），**reader 在 writer 持续更新下无法完成足够的成功读取来耗尽迭代**——这本身还不足以归因到 OHOS、pthread 或 CK 内存序。五轮等价的不收敛只说明根因在 writer/reader 节奏交互本身，非 affinity/stall/二次读/STEPS。

### 7.3 线程数阈值对照（15 组可靠复测）

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

### 7.4 ck_sequence 调查最终结论（收紧表述）

`ck_sequence 20 1` 在鸿蒙真机上的超时是**非确定性 liveness/竞争现象**：

- 程序仍在运行（retries 持续增长），不是死锁、不是 assertion 失败、不是 pthread create/join 缺陷（基线 probe 已排除）、不是单字段原子缺陷（probe 已排除）。
- reader 在 writer 持续高频更新下无法完成足够成功读取来耗尽 1M STEPS，writer 退不出（不打印 `updates made`）。
- 逐层剥离 affinity/stall/二次读/STEPS 均未改变不收敛行为——根因在 writer/reader 节奏交互本身，非任一单一上游逻辑项。
- 15 组线程数复测无任何线程数三次稳定通过、不存在干净阈值——是非确定性抖动。
- **不足以归因到** OHOS pthread、CK 内存序缺陷；也**不是** recipe bug（test_package smoke 1/1 Passed）。
- **不继续重复 n=2 或继续降 STEPS**——不能改变正式测试"不稳定"的结论。

---

## 8. 全调查最终判定

1. **concurrencykit/0.7.2 不能推正式分支**——上游回归 15/24 通过、9 项超时，ck_sequence 经逐层剥离 + 15 组复测确认非确定性 liveness/竞争，不满足"上游回归已通过"条件。
2. **manifest.yaml 已更新为 `cases: 24, passed: 15, status: blocked`**——记录真机实测结论，note 含 ck_sequence 逐层剥离 + 15 组复测的完整证据摘要。
3. **不归因到 OHOS pthread / CK 内存序缺陷**——所有表述收紧到证据支持的范围：真机上的非确定性 liveness/竞争问题，归因未定。
4. **不创建 `feat/concurrencykit-0.7.2`**——推送更新后的 `codex/concurrencykit-0.7.2-validate` 验证分支（含 manifest.yaml 更新 + 本文档补充），暂不创建 feat。

---

## 9. 文件清单

- 本文档：`archives/c/concurrencykit/0.7.2/BLOCKED.md`
- 逐项证据：`archives/c/concurrencykit/0.7.2/PER-ITEM.md`
- barrier 完整日志：`~/ck-barrier.log`（5 变种全 passed，rc=0）
- 9 项死循环日志：`~/ck-{brlock,epoch,hp,pflock,rwlock,sequence,spinlock,stack,tflock}.log`
- 进度明细：`/storage/Users/currentUser/build_in_harmonyos/.ck-progress`（24 项逐项结论）
- conan create 日志：本轮 stdout（`concurrencykit/0.7.2: Already installed!` + smoke 1/1 Passed）
- ck_sequence 基线 probe 日志：
  - `~/ck-pthread-probe.log`（pthread 基线 rc=0）
  - `~/ck-sequence-probe.log`（单字段原子 rc=0）
  - `~/ck-sequence-abc-probe.log`（三字段无 fence rc=3，预期失败）
  - `~/ck-sequence-seqlock-probe.log`（真 seqlock 1w1r rc=0）
  - `~/ck-sequence-20t-run{1,2,3}.log`（20t 无 affinity 三轮全 rc=0）
- ck_sequence 逐层剥离日志：
  - `~/ck-sequence-upstream-affinity.log`（A 上游真实含 affinity rc=124）
  - `~/ck-sequence-upstream-noaffinity.log`（B 剥 affinity rc=124）
  - `~/ck-sequence-upstream-nostall.log`（剥 stall rc=124）
  - `~/ck-sequence-upstream-no-second-read.log`（剥二次读 rc=124）
  - `~/ck-sequence-upstream-steps10k.log`（降 STEPS=10k rc=124）
- 15 组线程数复测：
  - `~/ck-sequence-threshold/summary.log`（15 组完整 PID/rc/timeout/retries/updates/bytes）
  - `~/ck-sequence-threshold/n{2,4,8,12,16}-run{1,2,3}.log`（各组完整输出）
- 临时副本（跑完即恢复，未污染）：`/data/storage/el2/base/cache/ck-sequence-noaffinity/`（剥 affinity 版，STEPS=1M、stall/二次读全保留）
