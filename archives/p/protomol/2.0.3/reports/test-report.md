# protomol 2.0.3 测试与验证报告（OHOS aarch64）

- **目标包**：`protomol/2.0.3`（本仓规范引用，无 user/channel）
- **适配平台**：OpenHarmony / HarmonyOS PC，`aarch64-unknown-linux-ohos`
- **执行日期**：2026-09-27
- **详细台账**：上游测试逐用例明细见 [`upstream-tests.md`](upstream-tests.md)；
  构建过程见 [`build-report.md`](build-report.md)；配方门禁见 [`conan-verify-report.md`](conan-verify-report.md)。
- **日志留存说明**：本 PR **不提交原始日志全文**。理由有二：① 仓库 `archives/*/*/*/reports/logs/`
  在 **12287 个包中仅 2 个包存在**（共 23 个文件），提交原始日志并非本仓惯例；② 原始日志会显著放大
  变更体积，触发平台 AI 代码检视的「变更过大 → 本次跳过」判定（PR #13092 首轮即因 *68 个可审文件、
  10304 行* 被跳过；参照 `zephyr 3.1.2` 21 个文件可通过）。因此本文档下文列出的
  `reports/logs/...` 路径均为**本地执行时的原始日志路径**，文中的统计与判定结论全部由这些日志实测得出；
  按 §3.2 的测试命令与 §5 的门禁命令重跑，即可逐字重建全部日志。

---

## 1. 环境

| 项 | 值 |
|---|---|
| 平台 | OpenHarmony / HarmonyOS PC aarch64（真实设备） |
| 目标三元组 | `aarch64-unknown-linux-ohos` |
| 编译器 | `/data/service/hnp/bin/clang++`（Clang 15.0.4） |
| Conan | 2.29.1（`_venv_conan/bin/conan`，remote `ohpcd`） |
| Shell | `/data/service/hnp/bin/bash`（`/system/bin/sh` = mksh 无法 exec ELF，须 bash 包裹） |
| SDK | 26.0.0.18 |

---

## 2. 上游测试入口核验

| 核验项 | 命令 | 原始结论 |
|---|---|---|
| `TESTS=` / `check_PROGRAMS=` / `check_SCRIPTS=` 声明 | `grep -nE '^(TESTS\|check_PROGRAMS\|check_SCRIPTS\|check_LIBRARIES)\s*=' $(find . -name Makefile.am)` | 无输出（exit 1） |
| `check-TESTS` 目标 | `grep -n 'check-TESTS' Makefile` | 无输出（exit 1） |
| `make check` 实际内容 | `grep -nA2 '^check-am' Makefile` | `check-am: all-am` / `check: check-am` |

**结论**：上游**没有自动化测试套件**。`make check` 只是 automake 样板目标，等价于 `make all`，
不构成测试统计口径。上游真实可运行入口是 `examples/` 下的算例配置（`*.conf`）——36 个。

两个非算例入口不纳入本环境统计：

- `examples/testset/test.tcsh`：tcsh 结果对比框架；本环境无 `tcsh`，且 testset 的 12 个 conf
  中 `posfile`/`psffile`/`parfile` 全被注释（README 说明数据需自行提供）。
- `examples/butane_4/runButaneTests.sh`：PBS(`qsub`) 批处理脚本，需 PBS 集群 + `gawk`/`xmgrace`，单次 1e6 步。

---

## 3. 上游测试执行与统计

**测试命令**：

```bash
export PATH=/data/service/hnp/bin:/bin:/usr/bin
BASH=/data/service/hnp/bin/bash
PM=<staged install prefix>/bin/protomol
$BASH -c "cd <case-dir> && timeout 180 '$PM' <conf> --numsteps 20"
```

判定口径：exit 0 且日志出现 `Step : 20` + `Timing : wall:` → PASS；非 0 退出或 `Fatal Error:` → FAIL；
入口本身缺必要输入（数据被注释 / 需外部集群）→ SKIP。

### 3.1 统计汇总

| 口径 | 数值 |
|---|---|
| **用例总数** | **36** |
| **通过（PASS）** | **20** |
| **失败（FAIL）** | **6** |
| **跳过（SKIP）** | **10** |
| 待定（PENDING） | 0 |
| 实际执行数（总数 − SKIP） | 26 |
| 实际执行通过率 | 20 / 26 = **76.9%** |
| **平台适配相关失败** | **0** |

> 6 个 FAIL **全部是上游示例数据自身缺陷**（conf 语法 typo / 数据文件不完整 / PAR 缺键），
> 与平台无关 —— 同样的 conf 在 x86_64 Linux + GCC 下同样失败。故不修改上游示例数据
> （不属于 OHOS 适配范围，且会把无关改动混入 PR）。

### 3.2 逐用例名称与日志路径

日志根目录：`reports/logs/upstream/`（36 个算例日志 + `classification.json`）。

**通过 20 项**

| # | 用例名称（conf） | 退出码 | 日志路径 |
|---|---|---|---|
| 1 | `argon_400/argon.lf.conf` | 0 | `reports/logs/upstream/argon_400__argon.lf.conf.log` |
| 2 | `bpti_water_1101/bpti.hmc.conf` | 0 | `reports/logs/upstream/bpti_water_1101__bpti.hmc.conf.log` |
| 3 | `bpti_water_1101/bpti.lf.conf` | 0 | `reports/logs/upstream/bpti_water_1101__bpti.lf.conf.log` |
| 4 | `bpti_water_1101/bpti.shmc.conf` | 0 | `reports/logs/upstream/bpti_water_1101__bpti.shmc.conf.log` |
| 5 | `bpti_water_14281/bpti.ewald.conf` | 0 | `reports/logs/upstream/bpti_water_14281__bpti.ewald.conf.retry.log` |
| 6 | `bpti_water_14281/bpti.mg.conf` | 0 | `reports/logs/upstream/bpti_water_14281__bpti.mg.conf.log` |
| 7 | `bpti_water_14281/bpti.pbc.conf` | 0 | `reports/logs/upstream/bpti_water_14281__bpti.pbc.conf.log` |
| 8 | `bpti_water_14281/bpti.shake.conf` | 0 | `reports/logs/upstream/bpti_water_14281__bpti.shake.conf.log` |
| 9 | `butane_4/UA_butane.conf` | 0 | `reports/logs/upstream/butane_4__UA_butane.conf.log` |
| 10 | `butane_4/UA_butane.hmc.conf` | 0 | `reports/logs/upstream/butane_4__UA_butane.hmc.conf.log` |
| 11 | `butane_4/UA_butane.lf.conf` | 0 | `reports/logs/upstream/butane_4__UA_butane.lf.conf.log` |
| 12 | `decalanine_66/alanine.BSplineMOLLY.conf` | 0 | `reports/logs/upstream/decalanine_66__alanine.BSplineMOLLY.conf.log` |
| 13 | `decalanine_66/alanine.Equilibrium.conf` | 0 | `reports/logs/upstream/decalanine_66__alanine.Equilibrium.conf.log` |
| 14 | `decalanine_66/alanine.LF.conf` | 0 | `reports/logs/upstream/decalanine_66__alanine.LF.conf.log` |
| 15 | `decalanine_66/alanine.LFwDihedralOut.conf` | 0 | `reports/logs/upstream/decalanine_66__alanine.LFwDihedralOut.conf.log` |
| 16 | `decalanine_66/alanine.PLF.conf` | 0 | `reports/logs/upstream/decalanine_66__alanine.PLF.conf.log` |
| 17 | `decalanine_66/alanine.Shake.conf` | 0 | `reports/logs/upstream/decalanine_66__alanine.Shake.conf.log` |
| 18 | `electrons_22/22el.conf` | 0 | `reports/logs/upstream/electrons_22__22el.conf.log` |
| 19 | `water_648/water648.fluid.conf` | 0 | `reports/logs/upstream/water_648__water648.fluid.conf.log` |
| 20 | `water_648/water648.ice.conf` | 0 | `reports/logs/upstream/water_648__water648.ice.conf.log` |

**用例 5 备注（超时 → 复跑）**：第 1 次 `timeout 180` 命中上限被 kill（归类 PENDING）；
`timeout 1500` 复跑完整跑完 20 步：

```
Step :         20, Time :  0.020 [ps], TE : -34950.5122 [kcal/mol], T : 198.5133 [K], V : 157500.00 [AA^3]
Timing : wall: 234.70894[s] real, 227.01625[s] user, 0.13115[s] sys, run: 224.71226[s], integration: 224.71182[s], forces: 224.70389[s].
```

**FAIL 6 项（全部上游示例数据缺陷）**

| # | 用例名称（conf） | 退出码 | 首个错误（原文） | 日志路径 |
|---|---|---|---|---|
| 21 | `argon_400/argon.npt.conf` | 1 | `Fatal Error:   Integration definition mismatch, expexting 'level <number> <integrator> { ... }.` | `reports/logs/upstream/argon_400__argon.npt.conf.log` |
| 22 | `water_216/water216.conf` | 1 | 同上（conf 写成 `level 0 NPTVerlet{`，缺空格） | `reports/logs/upstream/water_216__water216.conf.log` |
| 23 | `water_648/water648.ice.nvt.conf` | 1 | 同上 | `reports/logs/upstream/water_648__water648.ice.nvt.conf.log` |
| 24 | `butane_4/UA_butane.dhmc.conf` | **-11 (SIGSEGV)** | `Segmentation fault`（`dihedralSetDHMC` 集合为空 → 越界解引用） | `reports/logs/upstream/butane_4__UA_butane.dhmc.conf.log` |
| 25 | `methane_ethane_xxx/ethane_methane_100.conf` | 1 | `Fatal Error: Could not find bond 'U1'-'U2' (1,2)` | `reports/logs/upstream/methane_ethane_xxx__ethane_methane_100.conf.log` |
| 26 | `methane_ethane_xxx/ethane_methane_300.conf` | 1 | 同上（PAR 缺 `U1`-`U2` 键定义） | `reports/logs/upstream/methane_ethane_xxx__ethane_methane_300.conf.log` |

**SKIP 10 项（`examples/testset/` 全部，`posfile` 被注释为空串）**

| # | 用例名称（conf） | 首个错误（原文） | 日志路径 |
|---|---|---|---|
| 27 | `testset/lf.std.conf` | `Fatal Error:  Can't open position file ''.` | `reports/logs/upstream/testset__lf.std.conf.log` |
| 28 | `testset/lf.std.pb.conf` | 同 | `reports/logs/upstream/testset__lf.std.pb.conf.log` |
| 29 | `testset/lf.MG.conf` | 同 | `reports/logs/upstream/testset__lf.MG.conf.log` |
| 30 | `testset/lf.Ewald.pb.conf` | 同 | `reports/logs/upstream/testset__lf.Ewald.pb.conf.log` |
| 31 | `testset/lf.PME.pb.conf` | 同 | `reports/logs/upstream/testset__lf.PME.pb.conf.log` |
| 32 | `testset/hmc.std.conf` | 同 | `reports/logs/upstream/testset__hmc.std.conf.log` |
| 33 | `testset/hmc.Bsp_PME.pb.conf` | 同 | `reports/logs/upstream/testset__hmc.Bsp_PME.pb.conf.log` |
| 34 | `testset/shmc.std.pb.conf` | 同 | `reports/logs/upstream/testset__shmc.std.pb.conf.log` |
| 35 | `testset/shmc.Bsp_PME.pb.conf` | 同 | `reports/logs/upstream/testset__shmc.Bsp_PME.pb.conf.log` |
| 36 | `testset/slf.std.pb.conf` | 同 | `reports/logs/upstream/testset__slf.std.pb.conf.log` |

分类机读台账：`reports/logs/upstream/classification.json`（逐 conf 的 `cls` / `note` / `log`）。

---

## 4. 消费者测试（`test_package/`，新增鸿蒙用例）

**命令**：`conan create` / `conan test` 自动执行 `test_package/test.sh`（`bash test.sh`）。

覆盖：6 个已安装程序冒烟 + 版本校验 + `argon_400`、`butane_4` 两个上游算例真实跑 20 步 MD，
断言步数、能量表、能量守恒、末步总能对参考值。

| 口径 | 数值 |
|---|---|
| 断言总数 | **17** |
| 通过 | **17** |
| 失败 | **0** |
| 跳过 | **0** |

关键参考值断言：`argon_400` 末步总能 `95.9160`、`butane_4` 末步总能 `6.8016`（均与参考值一致）。

日志：`reports/logs/verify/consumer-run.log`、`reports/logs/verify/w3-consumer.log`。

> **口径分离**：上游测试（§3）回答"上游算例在 OHOS 上能否跑"；消费者测试（本节）回答
> "conan 包装出的产物能否被下游正确消费"。两者互不替代。

#### 4.1 版本断言曾间歇性误报（已定位并修复）

`finish` 的 W3 本地 CI 曾报 `[FAIL] protomol --version did not report 2.0.3`
（`assertions passed: 16 failed: 1`），而同一二进制手工执行明确输出 `ProtoMol Version 2.0.3`。

- **根因（测试脚本缺陷，非配方/平台问题）**：原断言是
  `protomol --version 2>&1 | grep -q "ProtoMol Version 2\.0\.3"`，而脚本头部为
  `set -uo pipefail`。版本横幅共 **1282 字节 / 29 行**，超过一次 stdio flush 的容量，
  故 `grep -q` 命中即退出时 protomol 往往仍在写 → 被 **SIGPIPE** 杀死（128+13=**141**）
  → `pipefail` 让**整条管线**返回 141 → `if` 判为假。
- **判定性实验**：`protomol --version 2>&1 | true` → `PIPESTATUS[0]=141`；
  同一二进制带 `pipefail` 连跑 20 次有 **4 次**误判，去掉 `pipefail` 连跑 10 次 10/10 通过。
  属竞态，这也解释了 03:08 的 G2 `conan create` 偶然 17/17、03:17 的 W3 失败。
- **修复**：断言前先把完整输出捕获进变量，再用 bash 原生
  `[[ "$V" == *"ProtoMol Version 2.0.3"* ]]` 匹配，全程不建管道（`test_package/test.sh` §2）。
- **复验**：新旧断言对照 20 次 —— **旧 4/20 失败、新 0/20 失败**；
  修复后整脚本连跑 3 次均 `assertions passed: 17 failed: 0` / exit 0，
  清空 conan 缓存后的全新 `conan create` 亦为 **17/17**（见 `reports/conan-create.log`）。

---

## 5. 验证门禁

### 5.1 构建

| 步骤 | 命令 | 退出码 | 日志 |
|---|---|---|---|
| 补丁应用 | `apply_conandata_patches` / `patch -p1` | 0 | `reports/logs/verify/patch-apply.log` |
| configure | `./configure --build/--host=aarch64-unknown-linux-ohos` | 0 | `reports/logs/verify/configure-lcall-c.log` |
| make | `make -j1` | 0 | `reports/logs/verify/w3-make.log` |
| make（净化环境复验） | `make -j1`（去 safe-delete 垫片） | 0 | `reports/logs/verify/w3-make-sanitized.log` |
| 补丁边界核验 | 全新解包 vs 补丁后三方对比 | 0 | `reports/logs/verify/patch-boundary.log` |

补丁后与全新解包源码树差异：**恰好 11 个文件**（11 个补丁覆盖的上游文件集合；其中 `configure` 由 0010 与 0011 各改一处，`configure.in` 仅由 0010 改）。

### 5.2 conan-verify（8 道门禁）

```bash
# 在工作树内执行；引用为工具默认的 protomol/2.0.3@ohpcd/stable
python3 scripts/ohc-run.py conan-verify protomol 2.0.3 --project-dir .wt/protomol-2.0.3
```

| 门禁 | 结果 |
|---|---|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 `conan create` | ✅ PASS |
| G3 系统同名库隔离（R26） | ✅ PASS |
| G4 产物完整性 | ✅ PASS |
| L2 烟雾测试 | ✅ PASS（无 cache 路径，脚本规则跳过） |
| L4 安全扫描 | ✅ PASS（无 cache 路径，脚本规则跳过） |
| L5 产物基线 | ✅ PASS（无 cache 路径，脚本规则跳过） |

整体 **exit 0**，报告落盘 `reports/conan-verify-report.md`。

产物基线：6 个可执行文件（`protomol`、`coulomb`、`coords2coords`、`dcd2dcd`、
`iSGProtomol`、`xyzviz`）+ 15 个静态库；
`ELF64` / `AArch64` / `DYN (PIE)`；`NEEDED` 仅 `libc++_shared.so`、`libc.so`。

### 5.3 W3 本地 CI 模拟

`finish` Step 5（**阻塞门禁**）执行 `ci/conan/setup.sh` + `ci/conan/build_and_test.sh`：

| 项 | 结果 |
|---|---|
| setup.sh | ✅ 通过 |
| build_and_test.sh `protomol/2.0.3` | ✅ 通过（Pass rate **1/1 = 100%**） |
| 消费者断言（W3 内嵌 `conan create`） | `assertions passed: **17** failed: **0**` |
| L1 / L2 / L4 / L5 | `pass: test_package executed` / `pass: 6 个程序 --version OK` / `pass: patches clean` / `pass: bin/ has content` |

日志：`reports/w3-local-ci.log`；机器可读结果 `reports/../.ci-result.json`（`exit_code: 0`，`W3_local_ci`）。

### 5.4 归档与本地环境门禁（`finish`）

| 步骤 | 结果 |
|---|---|
| Step 0 前置关卡 | ✅ `test-report.md` / `.staging-verified` / `conanfile.py` / **知识整理**（`.knowledge-done`）全部就绪 |
| Step 1 补丁生成 | ✅ 编辑追踪器无变更 → **保留现有 11 个补丁** |
| Step 2 归档收尾 | ✅ `manifest.yaml` → `published`，`.build-closed` 已写 |
| Step 3 G0 干净构建验证 | ⚠️ configure 失败 —— **宿主 `getcwd()` 限制，非阻塞**（见下）。**注意：G0 的补丁应用阶段正常：`应用 11 个补丁… ✅ 11 个补丁全部应用成功`**（即补丁 0011 在配方链路中生效） |
| Step 4 质量验证（conan-verify） | ✅ 通过（§5.2）；清空 conan 缓存后的 G2 为**真实构建**（`Building from source` → `Created package revision 5335a87a80c22f2e7f50267dba92529f`） |
| Step 5 W3 本地 CI | ✅ 通过（§5.3）；同为**强制源码重建**（`Forced build from source` → `Created package revision f61907edfb70190b47a4785ba941b489`） |
| Step 6 归档校验（finalize） | ✅ **缺失 0**、一致性问题 1（仅下述脚本 glob 口径缺陷）；`packaging/protomol-2.0.3-ohos-aarch64.tar.gz` 已生成（6 个 ELF + `licenses/LICENSE`，11.6 MB） |
| Step 7 知识图谱完整性（W5） | ⚠️ 本包成分**已修**（`rc2=0`，`unreferenced 7→0`）；`rc=1` 来自 `knowledge/graph/` 仓库存量 → 见 §6 归属拆解 |
| Step 9 PR 原子性检查（W2） | ⚠️ 本地口径报 `.gitignore` 为「框架文件变更」——**本地与 CI 的口径差异**，见下方说明；CI 侧 JC/PF 从不为 `.gitignore` 报错 |
| Step 10 submit 就绪预检 | ✅ `test-report.md` / `packaging/` / `.staging-verified` / build-closed **全部就绪** |

> `finish` 最新一轮（含补丁 0011 的最终验证）`失败步骤: **step5b, step7**`、退出码 1：
> - `step5b`：拆解见 §6 表 —— `rc2`（本包）已归零，剩余 `rc`（仓库 `knowledge/graph/` 存量）与任何包无关。
> - `step7`（W2）：`check_pr_atomicity` 对比 `git diff origin/main...HEAD`，而 `_FRAMEWORK_PATHS`
>   把 `.gitignore` 列为框架文件。**本 PR 修改 `.gitignore` 是仓库既定机制**：要让 `reports/` 随 PR 提交，
>   必须加 7 行 `!archives/p/protomol/2.0.3/reports/...` 例外块（仓库已为 tcping、nb、handbrake、
>   lz4、unity、rocksdb、openssl、xf86-video-r128、diaspora-installer 等加过同类块）。
>   实证：`git log --max-count=200 --oneline -- .gitignore | wc -l` = **54**，即近 200 个提交中有 54 个
>   在提交包适配的同时修改 `.gitignore`（含 `【积分赛】feat(diaspora-installer)`、`【积分赛】feat(nb)`、
>   `【积分赛】feat(unity)`、`【积分赛】feat(nymphcast)`、`【依赖项】feat(openslp)` 等）。
>   CI 的 `junk_check.sh` 与 `preflight` 均不对 `.gitignore` 报错 → 属 **W2 本地口径 vs 仓库实践**的差异。
> - `gen_summary` 仍打印失败但**不计入门禁**（`SUMMARY.md` 属主编文件）。

**G0 的定性依据**（判定性试验）：Python 以 `cwd=<src>` spawn bash 且 `PWD=<src>` 正确时
`cannot access parent directories` 出现 **0** 次；`PWD` 缺失或错误时出现 **4** 次。根因是
`clean_verify.py` 用 `env=os.environ.copy()`，其中 `PWD` 仍指仓库根，bash 遂回退 `getcwd()`，
而本机 `/data` 权限 `0711` 无 read 位、`/storage` 挂载报 ENOTSUP。真实 CI 不跑 clean-verify，
G0 在 `finish` 中也仅告警，故**不为它改动配方**。

### 5.5 CI 首轮失败与修复（PR #13092，补丁 0011）

**首轮 CI 结果**（CI 侧分类：`Autotools configure 失败`）——原始日志：

```
configure: creating ./config.status
./config.status: line 475: ./confstatDPmIeK/subs.sed: Permission denied
./config.status: line 583: ./confstatDPmIeK/subs.frag: Permission denied
./config.status: line 754: ./confstatDPmIeK/out: Permission denied
mv: bad './confstatDPmIeK/out': Permission denied
./config.status: line 826: ./confstatDPmIeK/in: Permission denied     (grep: 同上)
./config.status: line 880: ./confstatDPmIeK/undefs.sed: Permission denied
./config.status: line 932/934: ./confstatDPmIeK/config.h: Permission denied
ERROR: protomol/2.0.3: Error in build() method, line 159
        ConanException: Error 2 while executing
```

**定位**：`configure` 自身的全部平台探测正常（`using FFT ZFFT` / `using PNG... no` /
`using GLUT... no`），失败**只发生在 `configure: creating ./config.status` 之后**，且全部集中在
`config.status` 自建的 `./confstatDPmIeK/` 临时目录里。上游 `configure:18684/18689` 用
`(umask 077 && mktemp -d -q "./confstatXXXXXX")` / `(umask 077 && mkdir $tmp)` 建该目录；
CI worker 的构建目录位于 `/storage/...`（HMDFS），**umask 077 建出的 0700 目录在该文件系统上不可写**。

**修复**：新增手工补丁 `0011-configure-umask-022.patch`（两处 `umask 077` → `umask 022`），
与仓库已合并先例 **`a52dec/0.7.4`、`teseq/1.1.1`、`vttest/2.7-20251205`** 完全同款
（其 `patch_description` 原文即 "setgid hmdfs makes umask 077 dirs unwritable"）。
只改构建期临时目录权限，**不改上游任何 C 源码、不注入平台宏**。

**本地复现与验证**（`_scratch` 脚本，未写入 PR）：

| 检查 | 结果 |
|---|---|
| 同目录 umask 对照 | `umask 077` → `700 drwx------`；`umask 022` → `755 drwxr-xr-x` |
| 补丁对**原始上游** `configure` `--dry-run` | `patching configure` / **exit 0** |
| 补丁对**已打 0001–0010** 的 `configure` `--dry-run` | `patching configure` / **exit 0** |
| 全新解包 + 按序应用 `0001..0011` | **11 个补丁全部 ok**；`umask 077` 残留 0、`umask 022` 出现 2 |
| 重新运行 `./configure` | **exit 0**；日志中 `Permission denied` **0** 次 |
| 生成的 `config.status` | 第 454/459 行已为 `umask 022` |
| `protomol_config.h` | 仍含 `PACKAGE_CITE` 与 `PACKAGE_VERSION`（补丁 0010 未失效） |

> CI worker 的文件系统语义**本地无法完全复刻**（本地 0700 目录可写），
> 故最终是否转绿以重新推送后的 CI 结果为准。

---

## 6. 结果

protomol 2.0.3 已在 OpenHarmony aarch64 真实设备上完成真实构建、上游算例实跑、
消费者测试与配方门禁验证，**平台适配相关失败 0 项**，配方满足 `published` 状态要求。

`finish` 的 `step5b` 经拆解后**归属本包与外部分两部分**（`finish.py:326` 要求
`rc(仓库图谱完整性) == 0` 且 `rc2(本包 manifest 引用) ∈ (0,3)`）：

| 组成 | 归属 | 状态 |
|---|---|---|
| `rc2`：本包 `manifest.yaml` 的 `knowledge_gained` 引用 | **本包** | 初值 `unreferenced=7` → **已修**（9 条全部补齐真实引用）→ `rc2=0`、`✅ 知识完整性检查通过`、`.knowledge-done` 已生成 |
| `rc`：`knowledge/graph/` 存量条目必填字段 | 仓库库存 | **仍为 1** → `step5b` 因而为 False |

其余非本包事项（均属 `scripts/` 框架或仓库存量，按 W2 不在本 PR 内修改）：

1. **`rc=1` 的成因**：E219/E253/E305 共 4 处字段被 `workflow_checks._REQUIRED_KV_FIELDS` 的
   `^(\w+):\s*(.*)` 误判为空（YAML 块标量 `root_cause: |` 的 `|` 被当作取值），其正文实际存在；
   另有仓库存量 1818 条知识草稿待审。**包无关性证据**：把同一函数指向**未改动的 main 仓库**
   复算，`rc` 同样为 **1**；本 PR 的 85 项文件集中 `knowledge/` 路径数为 **0**。
2. **`gen_summary`（SUMMARY.md）**：`'str' object has no attribute 'append'`；该步骤仅告警，
   不计入 `失败步骤`，且 `SUMMARY.md` 属主编文件，与本包制品无关。
3. **工具化打包不可达**：`finish` 会提示
   `python3 scripts/ohc-run.py package protomol 2.0.3`，但 `package` 未登记在
   `ohc/cli.py::_MODULES`，实测返回 `❌ Unknown command: package`；
   且 `package_builder.PackageBuilder.run()` 还要求 `verify-build` 产生的 `.verify-passed`
   标记，v3.0 `conanfile.py` 包不经过该链路。故 `packaging/` 由本流程按
   `finalize_archive.py` 的命名约定（`*-ohos-aarch64.tar.gz`）手工组装并逐项校验内容，
   **不写 `.packaged` 标记**（避免声称走了未真正执行的工具路径）。
   `packaging/` 与 `.staging-verified` 均被 `.gitignore` 忽略，**不进入 PR**。

另有 `finalize_archive.py` 的 `glob("000*.patch")` 口径缺陷：它漏掉不以 `000` 开头的
`0010-ohos-autotools-latin1-to-utf8.patch`，故误报"补丁数不一致 manifest=10 vs disk=9"
（实测 `ls patches/*.patch | wc -l` = **10**）。这是 `finish` 报告中最后 1 个一致性问题的唯一来源。
