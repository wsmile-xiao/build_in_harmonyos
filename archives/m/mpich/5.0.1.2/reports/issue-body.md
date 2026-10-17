**【申请人账号】**2301_80739235

**【队伍名称】**天天开心

**【申请日期】**2026/08/15

**【库名称】**mpich

**【版本】**5.0.1.2

## 关联 PR

PR：!5510

PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/5510

分支信息：`feat/mpich-5.0.1.2` → `main`

当前状态：open；当前 HEAD 为 `b038b77e200e8c2d9a39ddf9de277ce1d75f9256`

历史关联：!5446 已关闭，其源分支为 `feat/mpich-5.0.1.1`；该 PR 仅保留为替代前的历史记录，不作为当前评审对象。

当前路径：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C 候选

## 申请事项

本 Issue 不是直接申请路径 C 分值，而是请求评审委员会确认 MPICH 5.0.1.2 是否纳入路径 C 高难度挑战候选清单。若现有证据尚不足以纳入路径 C，则本 PR 仍按路径 A（基础适配）+ 路径 B（贡献创新）继续评审，不以路径 C 候选状态阻塞基础适配和可复用知识贡献。

## 申请原因

MPICH 5.0.1.2 是 NWChem 7.3.1、ScaLAPACK 2.2.3 和 Global Arrays 5.9.2 的底层 Fortran MPI provider。依赖拓扑要求先完成并正式发布 MPICH，下游才能用 `--build=never` 验证。适配范围同时覆盖 `src/mpi`、Hydra 进程管理、PMI、ROMIO、C/Fortran ABI 和 `test/mpi` 全量测试入口，不是单一编译参数或局部 smoke test 可以闭合的普通适配。

本库命中路径 C 候选的主要依据是特殊进程调度与全量测试成本：上游清单包含 1410 个独立逻辑测试入口；单次事务还需完成 Conan 构建、上游测试、消费者验证、进程残留扫描和 owner-only release。早期 CI #26157 因通用 3600 秒总预算不足而超时；包级预算生效后的旧 HEAD 构建已能完成上游测试前缀并进入 valid-abort 消费者验证，进一步暴露了显式 abort 终止语义与旧测试判据之间的冲突。

## 高难度分析

MPICH 的难点贯穿依赖解析、跨语言 ABI、目标机进程控制和长时全量测试四个阶段。仅证明库文件可交叉编译，不能证明 MPI rank 生命周期、Hydra/PMI 异常路径、Fortran 消费者或清理协议在 HarmonyOS PC 上正确。

**1. 依赖拓扑与跨语言 ABI**

适配必须同时维持 C API、`mpif.h`、`use mpi` 和 LLVM Flang runtime 的一致 ABI，并为 ScaLAPACK、Global Arrays、NWChem 提供可复用的底层 MPI provider。验证范围包括头文件、组件元数据、库布局、relocation，以及 C/Fortran 混合消费者；任一层偏差都会在下游放大。

**2. Hydra/PMI 特殊进程调度与清理协议**

Hydra launcher、proxy 和 MPI ranks 形成多级进程树，并存在 double-fork、`setsid()` detached descendant、launcher 提前返回和 bounded timeout 等路径。适配必须用 PID/starttime/token 绑定真实身份，联合进程树、进程组和 `/proc/*/environ` token 扫描，验证 TERM/KILL/reap、delayed canary、create-new gate、零残留和恢复运行；不能触碰或误杀任务外进程。

**3. 全量测试校验成本极高**

上游 `test/mpi` 盘点为 1410 个独立逻辑入口，历史完整执行达到 1410/1410（100%）。内部重复配置与原始执行计数仅保留在本地证据审计中，不作为公开库存重复计数。单次真机事务持续时间超过通用 CI 的 3600 秒预算，并且必须在同一快照内完成构建、测试、消费者和清理终态，不能拼接不同设备、不同 HEAD 或局部输出替代。

## 已完成的证据材料

1. 软件 PR #5510 已推送 MPICH 5.0.1.2 配方、补丁、测试和 E327/E328/E329 配对知识草稿，当前 HEAD 为 `b038b77e200e8c2d9a39ddf9de277ce1d75f9256`。
2. r62 历史真机证据完成上游 1410/1410（100%）后，暴露 `test_process_control detach` 的 15 秒已清理 timeout 合同缺口；该失败被保留并完成 clean release。
3. r64 证明启动后 4 秒 canary 早于 15 秒 cleanup，不能表示 post-cleanup escape；r65 随后以 15/15 Python 生产路径矩阵和 5/5 实际 C gate 闭合 create-new token gate 协议。
4. r67 的同快照 W3、Conan RC0、上游全量测试和 clean release 属于 MPICH 5.0.1.1 历史证据。5.0.1.2 等价性报告 SHA-256 `ca7dbf9ca7d6d0625bc5306b324e51ccc0f2e07955de6dab104e7cb93185c222` 证明 58 个实质文件逐字节不变、3 个文件仅替换包版本坐标、知识草稿仅替换冲突编号；该报告不是 fresh 5.0.1.2 W3。
5. valid-abort 定向验证通过 2/2 生产模式、4/4 负向场景、26/26 单片段删除变异和 C11 `-Wall -Wextra -Werror`，结果 SHA-256 为 `93df84e25ade8b321a7588a2c045b101f85a950824e29218eda2fbbcb02403b6`。
6. 完整 41-patch 集合在 Git、GNU patch 2.7.6 和 patch_ng 中全部完成正向与反向重放，三份正向 tree 一致，反向 tree 与官方源码逐字节一致；结果 SHA-256 为 `72518c0a6415cca359b8783297abcc52ba91107fc2d92ec56df2bf7ed9eb2c9f`。
7. Buildbot builder 1 / #26404（global buildid 29243、buildrequestid 39046）绑定旧 HEAD `0cef5d233729891093e007ad5993787ff60a5a4a`，在完成上游测试前缀后因旧 valid-abort 判据要求 `valid-int-max` 返回零而失败。该失败已由 E329 对应修复闭合，但它不能代表当前 HEAD；`b038b77e200e8c2d9a39ddf9de277ce1d75f9256` 尚无 exact-current-HEAD CI。

## 知识库查重情况

已对 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc` 和 `knowledge/operations` 检索 `managed MPI command exceeded`、`detached descendant`、`Hydra timeout`、`process-control timeout`、`zero residue`、`WRAPPER_CPPFLAGS`、`non-relocatable paths`、`valid-int-max` 和 `disable-auto-cleanup`。查重时没有语义等价条目；原草稿编号 E265 已被正式条目占用，因此本分支使用 E327、E328、E329 三组同 stem KV/MD 配对草稿，KV 均含 `draft: true`。后续 push 前仍按最新 `main` 重新执行合同查重，当前结论不替代未来快照的查重门禁。

## 可复用说明

E327 提炼 managed MPI runner 面对 double-fork/session-detached descendant 的通用闭环：launcher 返回但 descendant 仍存活，或 Hydra 保持运行直到 bounded timeout 时，清理后才能发布 create-new token gate。只有内层完成零残留、armed token 与 escape PID 证据精确、gate 后仍无 delayed canary 且 fresh smoke 通过，才能接受 containment 路径。普通超时、错误 executable/mode、缺证据、重复 gate 或残留进程仍必须失败。该方法可复用于其他包含 launcher/proxy/rank 多级进程和 detached descendant 的 MPI 类软件。

E328 提炼 Autoconf 工具链 wrapper 的可迁移性边界：Worker profile 中用于构建的本机 include 路径不能经 `CPPFLAGS` 固化进 `mpicc`、`mpicxx` 或 Fortran wrapper。配方在 configure 前提供受控的 `CPPFLAGS=-DNDEBUG`，同时保留对源码、构建目录、Conan cache 和 Worker 本机路径的 fail-closed 扫描；该方法可复用于会把构建标志持久化到编译器 wrapper 或元数据的项目。

E329 提炼显式 abort 与自动清理选项的终止语义：`-disable-auto-cleanup` 不能把合法 `MPI_Abort` 转换为正常存活。测试不能只接受任意非零返回，而必须同时绑定 parent/spawned PID/PGID、唯一 Hydra proxy、PMI parser 无诊断、精确 armed marker、无 delayed canary、零残留和恢复 smoke；该方法可复用于显式终止语义变化后需要同步旧测试 oracle 的 launcher 类软件。

## 当前状态与边界

- PR #5510 当前为 open，HEAD 为 `b038b77e200e8c2d9a39ddf9de277ce1d75f9256`，尚未满足当前 HEAD CI 通过门禁。
- builder 1 / #26404 是旧 HEAD `0cef5d233729891093e007ad5993787ff60a5a4a` 的失败构建，仅用于证明旧 valid-abort 判据缺口；当前 HEAD 尚未触发 `/rebuild`，不得沿用该构建。
- r62/r64 是保留的失败证据，r65 是本地定向闭环，r67 是 5.0.1.1 历史真机证据；均不改写为 fresh 5.0.1.2 W3。
- 本 Issue 仅申请路径 C 候选确认，不宣称已获得 100/150/200 任一档分值，也不以候选身份绕过 CI、Review、discussion 或提审门禁。

## 建议验收项

1. PR #5510 完成 exact-current-HEAD CI，Buildbot `ci_pr_number=5510`、完整 `ci_revision=b038b77e200e8c2d9a39ddf9de277ce1d75f9256`、包路径和全部步骤终态一致且成功。
2. 上游 1410/1410 logical（100%）及对应原始执行零失败，新增进程控制定向用例 20/20（100%），原始日志、清单、摘要和哈希能够互相复核。
3. C/Fortran ABI、Hydra/PMI 异常路径、detached descendant containment、零残留、恢复运行和 owner-only release 均由同一有效快照或评审认可的等价性边界证明。

## 申请边界

| 路径 | 分值 | 说明 |
| --- | --- | --- |
| 路径 A | 1 分候选 | 完成 MPICH 5.0.1.2 基础适配，并以当前 HEAD CI 和完整测试为最终门禁 |
| 路径 B | 10 分候选 | E327 提供可复用的 managed MPI detached-descendant 清理与 fail-closed 验证方法 |
| 路径 C | 仅申请候选确认 | 依据特殊进程调度、依赖拓扑和全量测试成本申请专项终审，不直接声明分值 |
| 其他 | 不单独申报 | 不重复计算依赖项身份、历史失败次数或局部验证工作量 |

*最终以评审委员会审核结果为准。*

## 需要评审委员会确认的问题

1. 是否认可 MPICH 5.0.1.2 作为路径 C 高难度挑战候选。
2. 路径 C 对本库的最低验收证据是否必须包含 fresh 5.0.1.2 W3，还是可接受严格文件等价性边界与 5.0.1.1 r67 历史 W3 的组合证明。
3. 特殊进程调度、C/Fortran ABI、下游 provider 拓扑和超过通用 CI 预算的全量测试成本，应按哪一档专项标准复核。
4. 若当前暂不纳入路径 C，是否认可本 PR 先按路径 A + 路径 B 继续评审。
