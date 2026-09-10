# 【高难度挑战】binutils 2.46.0 HarmonyOS PC 适配

## 申请人信息

- **申请人账号**：`sawakage`（智能任务平台领取记录已确认）
- **队伍名称**：中国矿业大学鸿晕当头（参赛者已确认）
- **申请日期**：2026/09/08
- **库名称**：binutils 2.46.0
- **智能任务平台任务**：`#3485`，状态 `assigned`
- **认领时间 D0**：2026/09/08 19:59:25（北京时间）
- **期限**：平台 `dueDate` 当前为空；按指南七天推算为 2026/09/15 19:59:25，页面值优先
- **平台活动**：开源鸿蒙PC专项积分赛-依赖

## 关联 PR

- **PR**：尚未创建；先认领任务、提交并同步分支、完成 exact-HEAD 门禁
- **PR 链接**：尚未形成
- **分支信息**：`feat/binutils-2.46.0` -> `main`
- **当前状态**：任务已认领，本地工程与真机验证完成；Issue/PR 和平台提审待执行
- **当前路径**：路径 A + 路径 B 候选 + 路径 C 候选

## 申请事项

本 Issue 请求评审委员会确认 binutils 2.46.0 是否纳入路径 C 高难度挑战候选清单，
不直接申请路径 C 分值，也不把本地验证等同于赛事复审。若当前证据仍需补充，代码 PR
继续按成功适配候选接受常规 CI 和代码审查。

任务 `#3485` 已由 `sawakage` 认领，平台列在“专项积分赛-依赖”活动，但指南允许在适配中发现高难度后
调整为 B/C 申报。本 Issue 采用唯一前缀 `【高难度挑战】`，不与 `【依赖项】` 叠加；
请评审同时确认该任务的活动归类是否需要后台调整。

| 路径 | 分值 | 说明 |
|---|---:|---|
| 路径 A | 1 分候选 | Conan clean build、打包、消费者和真机运行均成功 |
| 路径 B | 10 分候选 | E547 草稿归纳 Clang `.addrsig` 与 GNU as 的通用互操作模式 |
| 路径 C | 仅申请候选确认 | 明确命中“含汇编等复杂架构”，最终以专项复审为准 |
| 其他 | 不单独申报 | gprofng 组件排除和平台差异只作技术边界说明 |

## 高难度分析

### 1. 明确命中复杂架构条件

官方 2.46.0 归档有 29,637 个条目、8,815 个 `.s` 和 7 个 `.asm` 文件。项目不是
单一 C 库，而是同时包含 BFD 多格式/多架构后端、opcodes、gas、ld、libctf、
libsframe、gprof 等工具链组件，并覆盖汇编、重定位、符号版本、动态加载和链接脚本。

本申请只把赛事路径 C 第 3 条“含汇编、闭源二进制、特殊调度等复杂架构”作为硬命中项。
运行时 Conan `required: []`，因此不以“依赖链庞大”作为申报依据；OHOS 工具链和
Linux 专用 gprofng 仅作辅助事实，不扩大解释。

### 2. 构建与测试跨越工具链自举边界

Clang 既是构建编译器，又要驱动本轮新生成的 GNU as/ld。测试还涉及 DejaGNU/Expect、
PTY 与 pipe 差异、HMDFS symlink/执行权限、OHOS ELF 签名、musl loader 和 libc++ ABI。
最终 clean run 从全新 Conan cache 构建测试闭包和 binutils，耗时 2684.96 秒。

### 3. 全量验证和失败归因可复现

源码清点 386 个 `.exp`。启用 379 个，其中 367 个执行驱动、12 个支持文件；另执行
libiberty 7 个目标。最终 DejaGNU 为 3419 PASS / 35 FAIL / 0 UNRESOLVED，98.99%；
消费者 16/16。分类器将 35 项逐项映射到 15 个根因类；结合日志上下文和对照试验
复核，未发现当前适配引入的失败。

## 已完成的证据材料

以下均为已完成的本地或 HarmonyOS PC 实测证据；分支尚未推送，故不把它们表述为
“PR 已推送证据”。

1. 官方归档 SHA256：`8608fe44ab7de645f6ad0a898313b75338842490d609adb85c9fb2827c376af2`。
2. 25 个补丁经 Conan `patch_ng` 对官方源码逐项应用，25/25 通过。
3. 最终输入 bundle SHA256：`61f2ab642e0405787a1af1fa34e47b9e12281eb9fd1d8a93d509348fc2beec79`。
4. `j039`：全新 `CONAN_HOME`，Conan create 退出码 0，367 个驱动完整结束。
5. 结果归档 SHA256：`8efd26e9be91e44d4deb7eb53a4d85ebc9320dc54481f00d392936b183d7c6f3`，138 项清单校验通过。
6. 上游：3419 PASS / 35 FAIL / 0 UNRESOLVED，98.99%；libiberty 930/930。
7. 安装包消费者：通用 13/13；GNU ld/objcopy/strip 原生签名执行 3/3。
8. `archives/b/binutils/2.46.0/ohos-failure-analysis.md`：35 项名称、现象、对照、影响和边界。
9. `runtime19/24/33/41`：GNU ld 与 SDK LLD、O3、libc++、DWARF/relocation 对照。
10. E547 知识草稿：Clang `.addrsig` 与 GNU as 文本汇编互操作。

本地原始日志与机器摘要已整理为 `binutils-2.46.0-c-evidence.zip`；创建 Issue 时上传
该附件并在正文补充平台生成的附件 URL。正式 PR/CI 产生后，以官方在线日志为主、
附件为本轮真机对照证据。

## 当前状态与边界

- 2026-09-08 公开任务接口显示 `#3485` 为 `assigned`、`claimer=sawakage`、
  `claimedAt=2026-09-08T11:59:25Z`，精确分支为 `feat/binutils-2.46.0`。
- 对官方仓库精确分支执行 `git push --dry-run` 返回 `[new branch]`，证明当前认证与
  官方项目写权限可用，但没有创建远端分支。
- PR 代码候选已完成本地与 HarmonyOS PC 验证；官方仓库 CI、AI 检视和专项复审尚未执行。
- `make check` 原始退出码为 2，因为保留了 35 个真实 FAIL；配方解析所有汇总并按路径 C
  规则验收，不修改 verdict。
- gprof 上游发现 2 个入口，但设备配置 `gprof_cv_sys_native=no`，实际 0/0；gprofng 的
  7 个 `.exp` 随 Linux 专用 collector 显式关闭。两项均未写成通过。
- 当前功能分支已 rebase 到官方 `main=7285d0428`；对应 binutils 目录和规则模板无
  上游重叠。配方/测试输入与 final39 逐字一致，finish 生成的 W3 状态为通过；官方
  PR CI 尚待创建 PR 后执行。
- 本 Issue 只申请候选确认，不宣称已经获得路径 C 分值。

## 建议验收项

| 必须保留的功能 | 环境 / 输入 | 验证入口 | 预期行为 / 阈值 | 上游测试覆盖 | 日志 / 制品 |
|---|---|---|---|---|---|
| AArch64 汇编、链接与 ELF 检查工具 | OHOS 6.0 armv8 profile；官方 2.46.0 源码 | fresh-cache `conan create` | create 返回 0；包内 CLI 可执行 | binutils、gas、ld 五套 summary | `final39/conan-create.log`、package manifest |
| 完整上游可执行驱动 | 379 个启用 `.exp` 文件 | `make -k -j1 check` | 367 个驱动结束；无 ERROR/abort；普通通过率 >90% | 3419 PASS / 35 FAIL / 0 UNRESOLVED | `analysis/summary.json`、五套 `.sum/.log` |
| 安装包消费者 | 打包后的 as/ld/ar/nm/objdump/readelf/strip | `test_package` 两个入口 | 通用 13/13、原生 3/3 | build-tree 测试之外的 package 边界 | `conan-create.log` 5951-6085 行附近 |
| OHOS 原生执行与签名 | GNU ld、objcopy、strip 产物 | `native-test.py` | 三个程序签名后输出 `binutils native consumer: 2460` | ld 运行场景的包后验证 | native output、签名记录 |
| 保留失败解释 | 35 个最终 FAIL | 分类器 + 日志/对照人工复核 | 35/35 名称映射；当前适配引入项 0 | 15 个根因类 | `ohos-failure-analysis.md`、runtime19/24/33/41 |
| 提交门禁 | rebase 后 exact HEAD | `finish`、W4、官方 CI、`/ai review` | `.ci-result.json` 有效；W4 P0/P1=0；远端检查闭环 | 仓库全套门禁 | 后续 PR/CI URL 与审计报告 |

## 申请边界

最终以评审委员会审核结果为准。Issue、PR 与智能任务平台任务由参赛者在登录态完成关联；
复审通过后再参加路径 C 征文活动。

## 需要评审委员会确认的问题

1. 是否认可 binutils 2.46.0 以“含汇编等复杂架构”进入路径 C 候选。
2. 是否认可 98.99% 以及 35 项非适配缺陷归因满足路径 C 测试口径。
3. 是否接受 gprof 0/0 和 gprofng 显式组件关闭的当前边界，或需增加指定验证。
4. 路径 B 的 E547 知识草稿是否需另建 `【知识库扩展】` Issue。
5. 任务 `#3485` 当前属于“专项积分赛-依赖”活动，改用唯一 C 前缀后是否需要后台调整活动归类。
6. 若当前暂不纳入路径 C，是否允许成功适配 PR 先按已确认路径继续评审。
