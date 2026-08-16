# 知识库扩展 Issue 提交材料（路径 B）

## 基本信息

- 【申请人账号】`gcw_xUcfzZDz`
- 【队伍名称】湖北文理学院理工学院+死脑子快想啊
- 【申请日期】2026/08/12
- 【库名称】`activity-aware-firefox`

## 关联 PR

- PR：#5120
- PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/5120
- 分支信息：`feat/activity-aware-firefox-0.4.2-git20250816.c6082f37` → `main`
- 当前提交：以关联 PR 的最新提交为准
- PR 状态：已创建，等待官方 CI 与专家评审

## 申请路径 B 的理由

上游 wrapper 在进入 Firefox profile 管理前，硬编码调用 KDE
`plasma-activities-cli`、X11 `xdpyinfo`、`kdialog` 和桌面通知命令。
OpenHarmony 不提供 KDE Activities 的等价服务；简单补一个缺失命令或写死
默认 UUID 会混用用户 profile，不能解决同类桌面 wrapper 的可移植性问题。

本次不是单个编译宏或仅让脚本启动的 patch，而是抽象出“桌面上下文提供器”
模式：保留 KDE 自动发现；同时允许 OpenHarmony launcher、系统参数桥或产品
workspace manager 显式提供稳定 ID/名称；限制进入路径的 ID 字符集与长度；
把显示几何和 GUI 通知降为可选能力；增加可确定验证的 provider probe，并对
实际包内脚本运行 profile 创建、复用、路径选择和参数转发流程。

推后价值：可推广到任何把 workspace、desktop session、portal、display
utility 或通知命令硬编码进 wrapper 的跨平台迁移。

## 知识库查重与新增价值

- 新增 draft：`knowledge/drafts/E318-draft-1143.kv`
- 配套说明：`knowledge/drafts/E318-draft-1143.md`
- 拟提升编号：E318（最终编号由知识库主编确认）
- 条目主题：Desktop wrapper hard-codes KDE/X11 services unavailable on OpenHarmony
- 查重关键词：`desktop wrapper`、`KDE Activities`、`plasma-activities-cli`、`xdpyinfo`、`kdialog`、`explicit context provider`、`OpenHarmony`
- 覆盖判断：现有条目未完整覆盖“桌面专有上下文发现与实际业务流程解耦、显式 provider 注入、安全路径 ID、完整 wrapper 流程验证”的组合方案，本条目增量在于可复用的 provider 契约与禁止假 shim/随机 ID/仅 probe 测试规则。

## 证据材料

| 项目 | 内容 |
| --- | --- |
| 原始失败 | 无 KDE 环境出现 `Requirement plasma-activities-cli missing`；无 X11/GUI helper 时出现 `xdpyinfo: not found`、`kdialog: not found` |
| 修复方案 | `patches/0001-activityfirefox.patch`；当前提交见关联 PR 最终 HEAD |
| 构建验证 | Conan 2.29.1；host=`OHOS/6.0 armv8`、build=`Windows x86_64`；`conan create` 成功；recipe `9a07cea5fd7bf48a91027b650df0389a`，package revision `0519d27386be903d3dcb8ebce0bc7414` |
| 上游测试 | `0/0（N/A）`；上游未提供自动化测试套件，没有写成 100% |
| 消费者验证 | 对 Conan 产出的实际 `bin/activityfirefox` 执行 14 项新增断言，`14/14 PASS` |
| 审查证据 | 独立 W4 审计已通过，P0/P1 问题为 0；实际包内脚本复测结果为 `14/14 PASS` |
| 当前 CI | PR #5120 已触发官方 CI #21101；提交材料时状态为构建中，最终以 PR 页面结果为准 |

详细测试范围、执行输出和边界见
`archives/a/activity-aware-firefox/0.4.2+git20250816.c6082f37/reports/test-report.md`。

## 申请分值

- 路径 B 贡献创新：10 分候选
- 理由：核心价值是新增的可复用知识草稿和经过完整业务流程验证的 provider
  抽象，不重复申报路径 A 编译分或其他分值；最终以官方审核为准。

## 其他说明

- 本次只申报路径 B，不同时申报路径 A、依赖库附加分或 Patch C。
- 没有删除或修改上游测试；上游没有自动化用例，因此新增 14 项单独统计。
- 本地交叉构建阶段的 Conan runtime skip 没有计为通过；14 项结果来自随后直接调用
  实际 package revision 中的脚本。
- 真实 Firefox GUI 会话、OpenHarmony 产品 workspace provider 和最终 OHOS runner
  CI 是明确边界，未写成已验证。

## 需要官方确认的问题

1. 是否认可该“桌面上下文 provider 抽象＋完整 profile 流程验证”为路径 B（贡献创新，10 分候选）评审？
2. 是否认可 E318 草稿作为同类桌面 wrapper 适配的知识库新增条目？
3. 是否允许修复、验证证据和 PR 合并后，由知识库主编确认 E318 的最终编号与正文位置？
