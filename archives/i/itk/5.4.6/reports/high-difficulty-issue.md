# 【高难度挑战】itk 5.4.6 HarmonyOS PC 适配申请

【申请人账号】2301_80739235
【队伍名称】天天开心
【申请日期】2026/08/15
【库名称】itk
【版本】5.4.6

申请人：2301_80739235
队伍：天天开心
申请日期：2026-08-15
库名称：itk
版本：5.4.6

## 关联 PR

- PR：!5392
- PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/5392
- 分支信息：`2301_80739235:feat/itk-5.4.6` -> `OpenHarmonyPCDeveloper:main`
- 当前状态：OPEN
- 当前路径：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C 候选

## 申请事项

本 Issue 用于请求评审委员会确认 ITK 5.4.6 的 HarmonyOS PC 适配是否可纳入路径 C 高难度挑战候选清单，不直接申请或预先声明路径 C 分值。若现有证据仍不足以满足路径 C 的最终验收要求，本 PR 继续按路径 A + 路径 B 推进，不以候选申请阻塞基础适配和可复用知识贡献的正常评审。

## 申请原因

ITK 5.4.6 的最小 `ITKCommon` 配置仍会展开 NIFTI、KWSys、TIFF、libpng、VNL、MetaIO、KWStyle 和 ExternalData 等多层内嵌组件，不是修改一个平台宏即可完成的常规交叉编译。HarmonyOS PC AArch64 的 DevEco clang 15/CMake 工具链先后真实暴露：NIFTI 错误要求独立 `libm`，两份 KWSys 与 TIFF 在未知系统上误选 Win32 源并包含 `windows.h`，PNG 仅按处理器字符串漏选 NEON 源，KWStyle 依赖网络下载且其 bundled Boost 调用目标 pthread 未声明的 cancellation API，以及完整上游测试依赖 14 个内容寻址 baseline。修复必须分别使用目标链接事实、正向 `WIN32` 与 POSIX API 能力探针、NEON intrinsic 编译探针、checksum-bound 本地源、`Threads::Threads` 符号探针和 manifest-bound CID 对象闭集，不能用 `__OHOS__` 条件宏、伪装 Windows、禁用测试或恢复网络回退。

完整上游闭环启用 `BUILD_TESTING=ON`，构建 2209/2209 个 Ninja edge，盘点并执行 618 个 CTest 入口；fresh 结果为 618/618（100%），failed/skipped/disabled 均为 0。多阶段源码选择、目标工具链语义、离线输入闭集、一次性真机失败定位和全量测试成本共同构成本次路径 C 候选申请依据。

## 高难度分析

1. **跨组件、跨构建阶段的系统性缺口**：问题分布在配置、内嵌工具构建、98% 源文件选择、最终链接和完整测试数据生成阶段；NIFTI、主 KWSys、KWStyle 内嵌 KWSys、TIFF、PNG、Boost 与 ExternalData 必须分别闭合，任一局部修复都不能代表整条构建图通过。
2. **不能依赖平台名的可移植修复约束**：CMake 对 HarmonyOS 的系统分类不完整，但目标实际提供 POSIX、NEON 和无需独立 `libm` 的能力。修复必须依据真实 API、intrinsic 和链接语义正向选择，并为能力缺失保留 fail-closed 负例，不能把未知系统默认成 Windows 或加入 OHOS 专用捷径。
3. **完整测试输入与执行成本**：上游 618 项测试会激活 KWStyle `ExternalProject`、bundled Boost 和 ExternalData。clean Conan worker 必须从 recipe export 中获得固定源码和 14 个 CID 对象，验证 manifest、路径、bytes、SHA-256、missing/extra/duplicate/link 边界并禁用 URL fallback；GitCode 的文本 PR patch 还要求先以 canonical Base64 运输、再在隔离 export 目录恢复并复核原字节。消费者测试与真机验证不能替代这 618 个入口。

## 知识库查重情况

提交前对 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations` 四个目录检索了 `ProcessWin32/tif_win32/NOT UNIX/POSIX capability`、`arm_neon/CMAKE_SYSTEM_PROCESSOR/filter_neon/undefined symbol`、`NIFTI_SYSTEM_MATH_LIB/NOTFOUND/libm`、`KWStyle/ExternalProject/offline source`、`ExternalData_OBJECT_STORES/CID/export_sources`、`missing binary patch data/Base64`、`pthread_setcancelstate/Threads::Threads/Boost capability`、`ITK_COMPUTER_MEMORY_SIZE/MemTotal` 与 staged tree/controller binding。正式图谱和文档中没有语义等价条目；E140 只讨论平台名称兼容，E127 只识别缺失 pthread cancellation API 并给出 libomp 平台宏，E254 只讨论一般新增文件的 `export_sources()` 运输，E256 虽覆盖同一二进制 PR patch 症状但只删除可丢弃打包产物，均不能替代本任务对必需测试对象的可验证文本运输、具体能力选择、严格对象闭集和完整测试复核合同。E265-E273 是本任务随同一软件 PR 提交的 create-new 草稿，已从既有知识判断中排除。

## 可复用说明

E265-E273 可复用于三类通用场景：未知 CMake 系统在 Windows/POSIX 实现之间需要按真实 API 能力选择；目标编译器已支持架构 intrinsic 但构建系统仍仅按处理器名称选源；完整测试图依赖外部工具、可选 pthread API 或内容寻址 baseline，必须形成 checksum/manifest-bound 的离线输入闭集。E270 进一步覆盖 clean Conan worker 的 `export_sources()`、文本 PR diff 的 canonical Base64 运输与原字节恢复、runnable 默认对象根、空覆盖回退、non-runnable host 数据隔离、link/missing/extra/duplicate/hash fail-closed 和无 URL fallback。每个条目都写明适用条件、反例、验证方法和不得泛化的平台边界，可由其他大型 CMake/Conan 项目直接复核复用。

## 已完成的证据材料

- PR 已提交 ITK 5.4.6 Conan recipe、6 个可移植性补丁、消费者测试、manifest-bound ExternalData store、赛事报告和 E265-E273 成对知识草稿。
- 完整宿主上游验证：Ninja `2209/2209`，CTest `618/618`（100%），failed/skipped/disabled=`0/0/0`；清单和原始日志均有 SHA-256 绑定。
- 消费者与既有认证真机验证：`1/1` PASS；历史 r32 单次 launch 的构建、链接、运行、terminal/release 和两次 clean scan 均为 PASS。
- 当前 ExternalData 修复定向验证：文本运输 `6/6`、导出运行时 `8/8`，既有 store `12/12`、generate `8/8`、CMake readback `2/2`；fresh Conan export `15/15`，包含 14/14 个原始 CID 对象、992270 bytes、零 encoded 文件，逐文件 SHA-256 一致。
- 最终独立 W4：P0/P1/P2/P3=`0/0/0/0`；fresh Pre-PR 合同验证标题、唯一 OPEN Issue、上游 618/618、赛事正文和知识草稿均通过。

## 当前状态与边界

PR #5392 保持 OPEN，任务 192 已绑定，当前源分支由申请人账号维护。旧 exact-HEAD CI `#26137` 在 KWStyle 构建后因 clean Conan export 缺少 CID 对象失败；后续 CI `#26212` 在 `checkout-pr` 因文本 PR patch 缺失二进制 payload 而零 recipe 执行终止。本次修复用 canonical Base64 文本运输 14 个对象，在 `export_sources()` 恢复并按原 manifest 校验，已完成上述离线正负例和 fresh export 验证；replacement current-HEAD CI 尚待平台执行。当前不把旧 CI、旧 AI Review 或路径 C 候选申请表述成最终通过，也不声称评审委员会已经授予分值。

本次 ExternalData 变更只闭合 host 上游测试输入运输；用户明确不要求为 CI 准备重复真机。既有 r32 真机证据保留为已完成消费者运行验证，不伪装成当前 recipe 的新 W3。最终合入仍以当前 HEAD 的 AI Review、Buildbot CI、讨论解决状态和评审委员会意见为准。

## 建议验收项

1. 当前 HEAD 的 Buildbot clean worker 能从 Conan export 获得全部 14 个 CID 对象，完整构建并通过仓库门禁。
2. 当前 HEAD 的 AI Review 达到 P0=0、P1=0，且 PR 赛事模板、618/618 上游测试和 1/1 消费者测试证据可回读。
3. 评审委员会确认上述多组件能力探针、离线输入闭集和完整测试成本是否达到路径 C 候选要求；若不足，明确还需补充的最低证据。

## 申请边界

| 路径 | 分值 | 说明 |
|---|---:|---|
| 路径 A | 基础适配候选 | 已完成 recipe、补丁、构建与消费者验证 |
| 路径 B | 10 分候选 | E265-E273 为查重后无等价项的成对可复用知识草稿 |
| 路径 C | 仅申请候选确认 | 不直接声明分值，以评审委员会验收为准 |
| 其他 | 不单独申报 | 不拆分知识 PR，不重复申报同一软件 |

最终以评审委员会审核结果为准。

## 需要评审委员会确认的问题

1. 是否认可 ITK 5.4.6 作为路径 C 高难度挑战候选。
2. 路径 C 的最低验收证据是否还需要超出当前源码、测试、CI 和真机闭环的补充材料。
3. 当前多组件能力探针与 manifest-bound 离线输入闭集是否可作为高难度与可复用性的有效证据。
4. 若当前暂不纳入路径 C，是否认可本 PR 先按路径 A + 路径 B 继续评审。
