**【申请人账号】** 2301_80739235
**【队伍名称】** 天天开心
**【申请日期】** 2026/08/24
**【库名称】** wxwidgets 3.3.3

## 关联 PR

PR：!6427

PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6427

分支信息：feat/wxwidgets-3.3.3 -> main

当前状态：open

当前路径：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C 候选

## 申请事项

本 Issue 请求评审委员会确认 wxWidgets 3.3.3 是否纳入路径 C 高难度挑战候选清单，不直接申请或声明路径 C 分值。若现有证据不足以纳入路径 C，本 PR 仍按路径 A（基础适配）+ 路径 B（贡献创新）继续评审。

## 高难度分析

wxWidgets 不是单一算法库，而是覆盖基础设施、事件系统和 GUI 窗口栈的跨平台 C++ 框架。完整目标平台适配需要同时处理平台后端、工具链与运行时能力、上游测试矩阵和真实设备闭包；当前 PR 已完成无 GUI 的静态 wxBase 交付，但不把这一边界内的通过结果解释成完整 GUI 适配完成。

1. **GUI 平台后端与窗口系统边界**

   本候选声明 `HD3_COMPLEX_ARCHITECTURE`：含汇编、闭源二进制、特殊调度等复杂架构；本库命中的是 GUI 事件循环与平台调度，不声称存在汇编或闭源二进制。上游公共接口位于 `include/wx`，公共实现位于 `src/common`，现有窗口后端分布在 `src/msw`、`src/gtk`、`src/osx`、`src/x11` 和 `src/unix`。目标平台没有可直接复用的 wxWidgets GUI 后端；若完成完整 GUI 栈，需要为窗口、显示、输入、事件循环、剪贴板、字体与绘制能力建立目标端实现，并证明生命周期和线程语义。当前 PR 使用 `wxUSE_GUI=OFF`，因此只证明 wxBase，不宣称上述窗口能力已经交付。

2. **构建、运行时能力与测试矩阵**

   配方需要在 Conan/CMake 交叉编译、libc 内建 iconv、locale、文件系统、编码、XML 与调度能力之间保持一致语义。20 个补丁使用通用 POSIX 或运行时能力探测，不加入 OHOS 条件编译宏。上游 Catch2 `test_base` 的冻结清单为 429 项；目标设备实际结果为 399 PASS 与 30 个带 id、path、reason 的 expected SKIP，failed=0，完整分母 nonfailed=429。能力缺失不能靠删除测试或缩小分母掩盖。

3. **跨阶段证据闭包与真实设备验证**

   源码必须绑定 GitHub Release asset `471278068` 的名称、大小和官方 SHA-256；构建产物、测试清单、runner、事务 WAL 与设备结果必须属于同一冻结快照。W3 `wxwidgets-333-w3-019fb34c-r86ar` 在 `10.62.148.108:2222` 完成唯一一次 launch，除上游 429/429 nonfailed 外，CTest 为 1/1、consumer 为 1/1，释放后远端根为 ABSENT 且本任务进程为 ZERO。历史失败事务均保留且不跨快照拼接。

## 已完成的证据材料

- 官方源码：wxWidgets v3.3.3 Release asset `wxWidgets-3.3.3.tar.bz2`，asset id `471278068`，SHA-256 `81b09d6dd9f1ed9301f8c55a968a488d0491f264dc2bab19a7e407ac67009482`。
- 基础适配：Conan 配方、CMake 静态 wxBase 配置、20 个可重放补丁、`test_package`、manifest 与 notes 已推送至 PR !6427。
- 构建与测试：W0、源码与依赖解析、W1、W2 已完成；真实设备 W3 为 429/429 nonfailed，CTest 1/1，consumer 1/1，并完成清理回读。
- 快照证据：W3 freeze SHA-256 `964179a3dec3daee25744350f5c98fed91e6e9f4b04f2f13390728bf0ffb0c97`，输入包 SHA-256 `a5d3fa0236955fd9bd8c6721eaab2d9899276f2b35bf558637cb986260f88d72`。
- 路径 B：已检索 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations`，没有等价覆盖 GitHub Release asset 身份绑定；同一 PR 提交 `knowledge/drafts/E2152-draft-WX33.kv` 与同 stem Markdown。E2152 适用于官方 Release asset 源完整性复核，不证明 GUI 能力，也不替代构建、测试或提审。
- 关联关系：唯一 OPEN Issue #2356 与 PR !6427 已完成正反向回读。

## 当前状态与边界

PR !6427 当前为 open。本模板正文生成时，current-HEAD CI 尚未触发；CI、AI Review 和提审结论必须以修正完成后的 PR 当前完整 HEAD 为准，不复用旧 HEAD 状态。

当前可交付范围是静态、无 GUI 的 wxBase。该结果不证明 wxCore GUI 窗口栈、显示、输入、绘制、剪贴板或完整桌面事件循环已适配，也不把 30 个 capability skip 说成对应能力已经实现。本 Issue 仅申请路径 C 候选确认，不宣称已满足路径 C 分值。

## 建议验收项

1. 核对 PR 当前 HEAD 的配方、20 个补丁和 `test_package`，确认构建入口可复现、源码及补丁不含 OHOS 条件编译宏，并由 Buildbot 对同一完整 revision 通过。
2. 核对 W3 冻结快照、429 项有序上游清单、30 个 reason-bound expected SKIP、CTest/consumer 结果及释放后清理状态，确认没有缩小分母或跨快照拼接。
3. 分开评估“当前 wxBase 交付质量”和“完整 wxWidgets GUI 平台后端的系统性难度”，由评审委员会决定现有证据是否足以进入路径 C 候选。

## 申请边界

| 路径 | 分值 | 说明 |
|------|------|------|
| 路径 A | 1 分候选 | 静态无 GUI wxBase 基础适配，最终以流水线结果为准 |
| 路径 B | 10 分候选 | E2152 配对草稿，最终以知识贡献评审结果为准 |
| 路径 C | 仅申请候选确认 | 不直接声明分值 |
| 其他 | 不单独申报 | 依赖任务身份仅作活动说明，不叠加路径分值声明 |

*最终以评审委员会审核结果为准。*

## 需要评审委员会确认的问题

1. 是否认可该库作为路径 C 高难度挑战候选。
2. 路径 C 的最低验收证据是什么。
3. 对于当前只交付并验证 wxBase、但完整库包含尚未实现的 GUI 平台后端这一边界，是否需要先完成目标端 GUI 后端才能纳入路径 C 候选。
4. 若当前暂不纳入路径 C，是否认可本 PR 先按路径 A + 路径 B 继续评审。
