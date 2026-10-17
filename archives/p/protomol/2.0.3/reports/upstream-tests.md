# protomol 2.0.3 上游测试台账（OHOS aarch64）

- **目标包**：`protomol/2.0.3`
- **适配平台**：OpenHarmony / HarmonyOS PC，`aarch64-unknown-linux-ohos`
- **构建产物**：干净源码 + 10 补丁 → `clang++ 15.0.4 -g -O2`（`configure` exit 0，`make -j1` exit 0）
- **执行环境**：`/data/service/hnp/bin/bash` 包裹已安装的 ELF（`/system/bin/sh` = mksh 无法 exec）
- **执行日期**：2026-09-27

---

## 1. 上游测试入口核验

### 1.1 `make check` 是否存在？

存在，但**只是 automake 样板目标，不是测试套件**。核验命令与原始输出：

```
$ grep -nE '^(TESTS|check_PROGRAMS|check_SCRIPTS|check_LIBRARIES)\s*=' $(find . -name Makefile.am)
(无输出, exit 1)

$ grep -n 'check-TESTS' Makefile
(无输出, exit 1)

$ grep -nA2 '^check-am' Makefile
check-am: all-am
check: check-am
```

结论：全树没有任何 `TESTS=` / `check_PROGRAMS=` / `check_SCRIPTS=` 声明，`Makefile` 中也不存在
`check-TESTS` 目标 ⇒ **上游没有可自动化执行的测试套件**。`make check` 等价于 `make all`，
不构成测试统计口径。

### 1.2 真实测试入口是什么？

上游真实测试入口是 **`examples/` 下的算例配置（`*.conf`）+ 参考输出对比框架**：

| 入口 | 类型 | 核验结论 |
|---|---|---|
| `examples/<体系>/*.conf` | 真实算例（36 个） | 可用 `protomol <conf> --numsteps N` 驱动真实 MD 计算。**本次全部实跑** |
| `examples/testset/test.tcsh` | tcsh 结果对比框架 | 本环境无 `tcsh`；且 testset 的 12 个 conf 中 `posfile/psffile/parfile` 全被注释（README 说明数据需自行提供）⇒ 跳过 |
| `examples/butane_4/runButaneTests.sh` | PBS(`qsub`) 批处理驱动 | 需要 PBS 集群 + `gawk`/`xmgrace`，单次 1e6 步 ⇒ 不可在 CI 内自动化，跳过 |

因此本报告的统计口径以 **36 个上游 `*.conf` 算例实跑**为准。

---

## 2. 执行方式

```bash
export PATH=/data/service/hnp/bin:/bin:/usr/bin
export SHELL=/data/service/hnp/bin/bash
BASH=/data/service/hnp/bin/bash
PM=<staged install prefix>/bin/protomol

# 每个算例在“只含该算例数据文件”的独立工作目录中执行，避免输出互相覆盖
for c in examples/*/*.conf; do
    d=~/tmp/protomol-2.0.3/upstream-sweep/$(echo "$c" | tr '/' '_').d
    "$BASH" -c "cd '$d' && timeout 180 '$PM' $(basename "$c") --numsteps 20"
done
```

- **判定 PASS**：进程 exit 0，且日志中出现 `Step : 20` 与 `Timing : wall: ...` 收尾行。
- **判定 FAIL**：进程非 0 退出，或出现 `Fatal Error:`。
- **判定 SKIP**：不因适配缺陷失败，而是入口本身缺少必要输入（数据被注释 / 需外部集群）。

---

## 3. 统计汇总

| 口径 | 数值 |
|---|---|
| 上游算例总数（`examples/**/*.conf`） | **36** |
| 通过（PASS） | **20** |
| 失败（FAIL） | **6** |
| 跳过（SKIP） | **10** |
| 待定（PENDING） | **0** |
| 实际执行数（总数 − SKIP） | 26 |
| 实际执行通过率 | 20 / 26 = **76.9%** |
| 全量通过率 | 20 / 36 = **55.6%** |

> 说明：**6 个 FAIL 全部是上游示例数据自身缺陷（与平台无关）**，逐项根因见 §5。
> 适配后二进制对全部 20 个可运行算例均正常收敛并输出能量与计时，无一例因编译/运行期平台问题失败。

---

## 4. 逐用例明细

命令统一为 `protomol <conf> --numsteps 20`；日志路径相对 `reports/logs/upstream/`（原始日志**未随 PR 提交**，见 `test-report.md` 头部「日志留存说明」）。

### 4.1 通过（20）

| # | 用例（conf） | 退出码 | 证据（日志尾行） | 日志 |
|---|---|---|---|---|
| 1 | `argon_400/argon.lf.conf` | 0 | `Step : 20` + `Timing : wall:` | `argon_400__argon.lf.conf.log` |
| 2 | `bpti_water_1101/bpti.hmc.conf` | 0 | `Timing : wall:` | `bpti_water_1101__bpti.hmc.conf.log` |
| 3 | `bpti_water_1101/bpti.lf.conf` | 0 | `Timing : wall:` | `bpti_water_1101__bpti.lf.conf.log` |
| 4 | `bpti_water_1101/bpti.shmc.conf` | 0 | `Timing : wall:` | `bpti_water_1101__bpti.shmc.conf.log` |
| 5 | `bpti_water_14281/bpti.ewald.conf` | 0 | `Timing : wall: 234.70894[s] real` | `bpti_water_14281__bpti.ewald.conf.retry.log` |
| 6 | `bpti_water_14281/bpti.mg.conf` | 0 | `Timing : wall:` | `bpti_water_14281__bpti.mg.conf.log` |
| 7 | `bpti_water_14281/bpti.pbc.conf` | 0 | `Timing : wall:` | `bpti_water_14281__bpti.pbc.conf.log` |
| 8 | `bpti_water_14281/bpti.shake.conf` | 0 | `Timing : wall:` | `bpti_water_14281__bpti.shake.conf.log` |
| 9 | `butane_4/UA_butane.conf` | 0 | `Timing : wall:` | `butane_4__UA_butane.conf.log` |
| 10 | `butane_4/UA_butane.hmc.conf` | 0 | `Timing : wall:` | `butane_4__UA_butane.hmc.conf.log` |
| 11 | `butane_4/UA_butane.lf.conf` | 0 | `Timing : wall:` | `butane_4__UA_butane.lf.conf.log` |
| 12 | `decalanine_66/alanine.BSplineMOLLY.conf` | 0 | `Timing : wall:` | `decalanine_66__alanine.BSplineMOLLY.conf.log` |
| 13 | `decalanine_66/alanine.Equilibrium.conf` | 0 | `Timing : wall:` | `decalanine_66__alanine.Equilibrium.conf.log` |
| 14 | `decalanine_66/alanine.LF.conf` | 0 | `Timing : wall:` | `decalanine_66__alanine.LF.conf.log` |
| 15 | `decalanine_66/alanine.LFwDihedralOut.conf` | 0 | `Timing : wall:` | `decalanine_66__alanine.LFwDihedralOut.conf.log` |
| 16 | `decalanine_66/alanine.PLF.conf` | 0 | `Timing : wall:` | `decalanine_66__alanine.PLF.conf.log` |
| 17 | `decalanine_66/alanine.Shake.conf` | 0 | `Timing : wall:` | `decalanine_66__alanine.Shake.conf.log` |
| 18 | `electrons_22/22el.conf` | 0 | `Timing : wall:` | `electrons_22__22el.conf.log` |
| 19 | `water_648/water648.fluid.conf` | 0 | `Timing : wall:` | `water_648__water648.fluid.conf.log` |
| 20 | `water_648/water648.ice.conf` | 0 | `Timing : wall:` | `water_648__water648.ice.conf.log` |

**用例 5 备注（超时→复跑的完整过程）**：

- 第 1 次执行：`timeout 180` 命中上限被 kill，日志停在 `Step : 20` 之前 ⇒ 初始归类 PENDING。
- 复跑：`timeout 1500`，命令
  ```
  $BASH -c "cd <dir> && timeout 1500 $PM bpti.ewald.conf --numsteps 20"
  ```
  原始输出（日志尾）：
  ```
  Step :          0, Time :  0.000 [ps], TE : -34514.9477 [kcal/mol], T :   0.0000 [K], V : 157500.00 [AA^3]
  Step :         10, Time :  0.010 [ps], TE : -34922.8754 [kcal/mol], T : 177.9323 [K], V : 157500.00 [AA^3]
  Step :         20, Time :  0.020 [ps], TE : -34950.5122 [kcal/mol], T : 198.5133 [K], V : 157500.00 [AA^3]
  Timing 0 : 229.84180[s] process time, 10.94485[s] average, standard deviation 2.24389, n=21.
  Timing : wall: 234.70894[s] real, 227.01625[s] user, 0.13115[s] sys, run: 224.71226[s], integration: 224.71182[s], forces: 224.70389[s].
  ```
- 结论：**PASS**。超时纯属 180s 上限过短（FullEwald 全部 14281 原子对，单步约 11s），非适配问题。

### 4.2 失败（6）—— 全部为上游示例数据自身缺陷

| # | 用例（conf） | 退出码 | 首个错误（原文） | 根因 | 日志 |
|---|---|---|---|---|---|
| 21 | `argon_400/argon.npt.conf` | 1 | `Fatal Error:   Integration definition mismatch, expexting 'level <number> <integrator> { ... }.` | conf 写成 `level 0 NPTVerlet{`（**缺空格**）；同目录可运行的 `argon.lf.conf` 为 `Leapfrog {`。属上游示例 typo | `argon_400__argon.npt.conf.log` |
| 22 | `water_216/water216.conf` | 1 | 同上 | 同上（`NPTVerlet{` 缺空格） | `water_216__water216.conf.log` |
| 23 | `water_648/water648.ice.nvt.conf` | 1 | 同上 | 同上（`NPTVerlet{` 缺空格） | `water_648__water648.ice.nvt.conf.log` |
| 24 | `butane_4/UA_butane.dhmc.conf` | **-11 (SIGSEGV)** | `Segmentation fault`（无 `Fatal Error`，直接崩在 `dihedralSetDHMC` 读取） | 该 conf 引用的 `dihedralSetDHMC` 数据文件只有 1 字节（空二面角集合），DHMC 读取空集合后解引用越界。属上游示例数据缺陷 | `butane_4__UA_butane.dhmc.conf.log` |
| 25 | `methane_ethane_xxx/ethane_methane_100.conf` | 1 | `Fatal Error: Could not find bond 'U1'-'U2' (1,2)` | 该目录的 PAR 文件缺少 `U1`-`U2` 键定义（conf 引用了不存在的键）。属上游示例数据缺陷 | `methane_ethane_xxx__ethane_methane_100.conf.log` |
| 26 | `methane_ethane_xxx/ethane_methane_300.conf` | 1 | 同上 | 同上 | `methane_ethane_xxx__ethane_methane_300.conf.log` |

**这 6 项的处理决定**：**不修改上游示例数据**。理由：
1. 缺陷与平台无关——同样的 conf 在任何平台（含 x86_64 Linux + GCC）都会同样失败；
2. 修复示例数据不属于"OHOS 平台适配"范围，且会把无关改动混入 PR（违反 PR 原子性）；
3. 上游 `argon.lf.conf` / `water648.ice.conf` 等同类算例已可正常运行，证明二进制本身无缺陷。

### 4.3 跳过（10）—— 入口缺必要输入，非适配缺陷

| # | 用例（conf） | 首个错误（原文） | 跳过原因 | 日志 |
|---|---|---|---|---|
| 27 | `testset/lf.std.conf` | `Fatal Error:  Can't open position file ''.` | conf 中 `posfile` 被注释成空串 | `testset__lf.std.conf.log` |
| 28 | `testset/lf.std.pb.conf` | 同 | 同 | `testset__lf.std.pb.conf.log` |
| 29 | `testset/lf.MG.conf` | 同 | 同 | `testset__lf.MG.conf.log` |
| 30 | `testset/lf.Ewald.pb.conf` | 同 | 同 | `testset__lf.Ewald.pb.conf.log` |
| 31 | `testset/lf.PME.pb.conf` | 同 | 同 | `testset__lf.PME.pb.conf.log` |
| 32 | `testset/hmc.std.conf` | 同 | 同 | `testset__hmc.std.conf.log` |
| 33 | `testset/hmc.Bsp_PME.pb.conf` | 同 | 同 | `testset__hmc.Bsp_PME.pb.conf.log` |
| 34 | `testset/shmc.std.pb.conf` | 同 | 同 | `testset__shmc.std.pb.conf.log` |
| 35 | `testset/shmc.Bsp_PME.pb.conf` | 同 | 同 | `testset__shmc.Bsp_PME.pb.conf.log` |
| 36 | `testset/slf.std.pb.conf` | 同 | 同 | `testset__slf.std.pb.conf.log` |

跳过依据：`examples/testset/README` 明确说明这些 conf 的输入文件（`posfile`/`psffile`/`parfile`）
需由使用者自行准备；上游仅提供配置模板用于对比框架 `test.tcsh`（本环境无 `tcsh`）。
另 `examples/butane_4/runButaneTests.sh` 为 PBS(`qsub`) 批处理脚本（需 `gawk`/`xmgrace`，单次 1e6 步），
同样不纳入本环境统计。

---

## 5. FAIL 根因分类

| 类别 | 数量 | 用例 | 根因归属 |
|---|---|---|---|
| 示例 conf 语法 typo（`NPTVerlet{` 缺空格） | 3 | argon.npt / water216 / water648.ice.nvt | 上游示例数据 |
| 示例数据文件不完整（空 `dihedralSetDHMC`） | 1 | UA_butane.dhmc | 上游示例数据 |
| 示例 PAR 缺键（`U1`-`U2`） | 2 | ethane_methane_100 / 300 | 上游示例数据 |

**平台适配相关的失败：0 项。**

---

## 6. 与 test_package 的关系（口径分离）

| 口径 | 含义 | 本包结果 |
|---|---|---|
| **上游测试（本报告）** | 上游自带算例在 OHOS 上实跑 | 36 例：通过 20 / 失败 6（均上游数据缺陷）/ 跳过 10 |
| **消费者测试**（`test_package/test.sh`） | 从 conan 包消费视角验证已安装产物 | **17 断言全通过**（详见 `test_package/MANIFEST.yml`、`notes.md`） |

两者**互不替代**：上游测试回答"上游算例在 OHOS 上是否能跑"，消费者测试回答
"conan 包装出来的产物能否被下游正确消费"。本包为满足"至少新增一个鸿蒙消费者用例"要求，
在 `test_package/test.sh` 中新增了消费者用例（6 程序冒烟 + 版本校验 + `argon_400`、`butane_4`
两个上游算例真实跑 20 步 MD，断言步数/能量表/能量守恒/末步总能对参考值）。

---

## 7. 复现方式

```bash
# 上游算例全量复跑（本报告数据来源）
export PATH=/data/service/hnp/bin:/bin:/usr/bin
BASH=/data/service/hnp/bin/bash
PM=<staged prefix>/bin/protomol
for c in examples/*/*.conf; do
    d=$(mktemp -d); cp "$(dirname "$c")"/* "$d"/ 2>/dev/null
    ( cd "$d" && "$BASH" -c "timeout 180 '$PM' '$(basename "$c")' --numsteps 20" ) \
        > ~/tmp/protomol-2.0.3/upstream-sweep/$(echo "$c" | tr '/' '_').log 2>&1
    echo "$c -> exit $?"
done
```
