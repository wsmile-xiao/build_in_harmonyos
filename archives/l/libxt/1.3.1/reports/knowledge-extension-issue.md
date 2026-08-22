<p align="center"><strong>知识库扩展 Issue 提交模版（路径 B）</strong></p>

**【申请人账号】**2301_80739235<br>
**【队伍名称】**天天开心<br>
**【申请日期】**2026/08/21<br>
**【库名称】**libxt/1.3.1

## 关联 PR

PR：!5975
PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/5975
分支信息：`feat/libxt-1.3.1` -> `main`
当前提交：以 PR #5975 顶部最新提交为准
PR 状态：开放中

## 申请路径 B 的理由

这不是 libXt 单个源码行的孤立修补，而是跨平台上游测试的通用证据问题：固定注册清单中可能包含因目标 ABI 或公共 API 表达能力而按上游设计条件跳过的测试。若把 TAP `ok ... # SKIP` 记为 PASS，会虚增通过率；若把这些注册项移出分母，又会隐藏上游覆盖。需要建立可复用的清单、预期 SKIP 白名单和分栏计数合同，分别证明 PASS、SKIP、FAIL、total 与 nonfailed。

推广价值：适用于 GLib TAP、CTest、JUnit、DejaGnu 等具有固定注册清单和条件不适用语义的跨平台测试套件，尤其适用于 32/64 位 ABI、可选系统调用、目标能力或公共 API 参数宽度导致的条件 SKIP。

## 知识库查重与新增价值

新增 draft：`knowledge/drafts/E336-draft-2301.kv` 与 `knowledge/drafts/E336-draft-2301.md`
拟提升编号：E336（最终编号由知识库主编确认）
条目主题：目标 ABI 条件 SKIP 的完整清单与透明结果计数
查重关键词：expected SKIP、conditional skip、upstream inventory、nonfailed、AArch64、UINT_MAX、SIZE_MAX、GLib TAP
覆盖判断：live `origin/main` `8e0d2cbf322ca9d9a5b271f80cb82c66be2af166` 的 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations` 已覆盖 Libtool `.la` shadow（E331/E236）和 HMDFS wrapper（E228/E330），但未覆盖固定上游清单中 ABI 条件 SKIP 的身份白名单、原因绑定及 PASS/SKIP/nonfailed 分栏合同；本条目的增量在于该跨框架结果证据模型。

## 证据材料

| 项目 | 内容 |
| --- | --- |
| 原始失败 | libXt 1.3.1 在 AArch64 上四个 overflow 注册项按上游源码输出 `# SKIP`；中央 Pre-PR 合同仍要求 `passed == inventory` 且 `skipped == 0`，无法表达真实终态。 |
| 修复方案 | 保留 20 项完整上游清单，冻结 U06/U10/U14/U18 的测试路径和精确原因 `overflow not possible in this config`，分别报告 passed、skipped、failed、total、nonfailed；新增 E336 配对草稿，不把 SKIP 冒充 PASS。 |
| 构建验证 | 最终 staged candidate 在真机 `10.62.215.229:2222` 完成一次 W3 launch（runner/outer SSH RC0，shared/static `conan create` RC0），独立 validator 通过，16 PASS + 4 exact expected SKIP / 20、consumer 2/2、总计 18 PASS + 4 SKIP / 22。精确 run、归档 SHA-256、HEAD tree、staged tree、runner 与 wrapper 由提交前外部不可变证据绑定，不在本 staged 报告内自引用。官方 finish 因旧本地环境缺失原始 tarball、G2/setup.sh 失败，未生成新的 `.ci-result.json`。 |
| 上游测试 | 20 项完整注册清单：16 PASS、4 个精确 expected SKIP、0 FAIL、20 nonfailed；分母不缩为 16。 |
| 消费者验证 | 两个独立 `test_package` consumer 均 PASS，并在 shared/static 两种构建中执行；独立计数为 2/2，不按构建变体重复扩充分母。 |
| 审查证据 | predecessor W4 仅绑定旧 tree，不能复用；最终独立 W4 必须单独绑定本 staged tree，审计结果、输入身份和 P0/P1/P2/P3 计数以提交前外部回读为准。 |
| 当前 CI | 旧 Buildbot #28987 在旧 PR HEAD 上因 `libX11-xcb.la` 残留 `/storage/Users/currentUser/usr/local/lib` producer prefix 失败；该 Build 的原始 Properties/step log 未作为当前证据哈希绑定。exact-HEAD CI 必须在 push 后重新核验。 |

测试框架迁移类：上游入口保持 `make -j1 check`，测试规模为 Alloc 18 项、Converters 1 项、Event 1 项，共 20 项；结果为 16 PASS、4 个目标 ABI 条件 SKIP、0 FAIL、20 nonfailed。配方增加两个安装包 consumer 作为补充验证，但不替代上游清单；独立总计为 18 PASS + 4 SKIP / 22，断言元数据 20 不计入分母。证明材料由最终 staged tree 对应的外部 W3 summary、结果归档和独立 validator 共同绑定。

## 申请分值

**路径 B 贡献创新：10 分候选**

理由：E336 把容易被误报为 `N/N（100%）` 的条件 SKIP 转化为可机械复核的跨框架证据合同，明确完整分母、精确允许项、原因漂移、unexpected PASS/SKIP 和构建变体去重边界，可复用于其他 ABI/能力条件测试套件。

*测试框架/工具链验证作为路径 B 证明材料，不重复申报额外分值。最终以官方审核为准。*

## 其他说明

- 本软件适配仍保留路径 A，路径 B 为随同一软件 PR 提交的新增知识；不单独申报路径 C。
- 本任务是 OpenJ9 0.59.0 Issue 1084 的真实前置依赖，对应 lowercase contrib 任务 3715；mixed-case `libXt/1.3.1` 历史行不领取、不绑定。
- 四个上游 SKIP 不会被写成 PASS，也不会从 20 项分母中删除。当前 Pre-PR 工具合同冲突会如实保留，不能用虚假统计绕过。
- 当前候选的官方 `finish ... built` 已按正规入口尝试，但旧本地 finish 环境在 G0 缺失原始 tarball、Conan G2 和 Step5 setup.sh 处失败；未手工创建或修改 `.ci-result.json`。真机 W3 与官方 finish 结论分开记录，不用 W3 冒充 finish PASS。
- 真机初始只读预检观察到 4 个其他任务进程，未终止或重配置它们；最终 launch preflight 在这些进程自然结束后回读为 blocking count 0、verdict PASS，随后才执行私有根下的单次 launch。独立 W4 仍必须绑定最终 staged tree 后才能提审。

## 需要官方确认的问题

1. 是否认可本 PR 按路径 B（贡献创新，10 分候选）评审
2. 是否认可该条件 SKIP 透明计数合同属于可跨库复用的适配知识
3. 是否认可修复 + 验证证据，并允许草稿在主编审核时确定最终编号
