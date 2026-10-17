# E545 — config.sub 组合校验必须按字段数选择 OHOS 模式尾缀

## 错误特征
原始 OS 表不接受 ohos，报 `OS 'ohos' not recognized`；补完 OS 表但组合表不匹配时，仍可能报 `Kernel 'linux' not known to work with OS 'ohos'`。全文已有 linux-ohos 不代表两个校验都完成。

## 触发条件
- Autotools 的 config.sub 将 kernel、os、obj 分开处理，并有最终组合验证。
- 引用既有知识或复制补丁时，源脚本与目标脚本的 case 表达式字段数不同。

## 根因分析
这是 E122/E268 推荐模式的适用边界反例，不是新的“添加 OHOS 白名单”方案。它们针对 `case $kernel-$os-$obj in`，使用 `linux-ohos*-`，末尾的连字符对应第三字段的分隔符。libwpg 发布源码实际是 `case $kernel-$os in`，待匹配字符串只有 `linux-ohos`，照搬带尾缀模式永远不能命中。

E072 已覆盖两字段表的修复。本次独立增量是证明两种已有方案不能直接互换，并用 case 表达式的真实字段数选择模式，而非版本年号或全文件 grep。

## 解决方案

### 推荐方案
1. 从官方 pristine 源码定位 OS 白名单和最终 kernel/OS 组合表，读出完整 case 表达式。
2. 两字段 `$kernel-$os` 使用 `linux-ohos*`；三字段 `$kernel-$os-$obj` 使用适应该版本 obj 语义的 `linux-ohos*-`，不能机械复制。
3. OS 表独立补入 `ohos*`。只修改 OS 表或只修改组合表都不足。
4. 生成最小正式源码补丁，`sh -n`、干净源码 dry-run 和 `sh config.sub aarch64-unknown-linux-ohos` 均须通过；完整输出不能归一成 linux-gnu-ohos。

### 禁止做法
- 不因全文存在 linux-ohos 就跳过最终组合表。
- 不照搬三字段尾缀到两字段 case，也不替换整个 config.sub。
- 不用显式 --host/--build 参数跳过原生识别链；不改生成 configure 来掩盖身份问题。

## 验证
libwpg 0.3.4 原生 r1 在 config.sub 报 OS ohos 不识别，未进入 configure。正式 `0002-config.sub.patch` 两个 hunk 分别修改 OS 表及两字段组合表；源码哈希 `b55fda9440d1e070630eb2487d8b8697cf412c214a27caee9df69cec7c004de3`。

r2 回读 canonical 为 aarch64-unknown-linux-ohos，完整 Conan create RC0、发布包 make check RC0（无注册测试程序）、消费者真实 WPG -> SVG 14 断言通过。原始日志 SHA-256 `610c5b5a979fcf895728af5de81168466b3f09ecb15ecc9d4a1a499acdb785c9`。该前轮证据不替代正式 finish 或比赛 CI。

该结论适用于任何字段拼接形式不一致的 shell case 校验迁移；对于单变量 `os=-linux-ohos` 的旧式解析器应按其自身分支分析，不套此表。

## 关联条目
- E072 已给出两字段 OS/组合白名单；E122/E268 是三字段的相似症状。本条只提交字段数/尾缀不可互换的反例与选择步骤。
- 已查 knowledge/graph、drafts、doc、operations 的 kernel-os、kernel-os-obj、two-field、两字段/后缀与 case expression；相关条目均已对照原文，未发现同一条件矩阵。


## 2026-10-13 CI 反例与修复增量

Even a tiny valid binary parser fixture can be lost by a text-only PR diff. Text encoding does not permit replacing it with an empty or header-only sample: validate the complete decoded size/hash before the original positive parser test reads it.

The original no-registered-upstream-tests boundary remains; a restored real consumer sample does not create new upstream tests. Keep 0/0 not-applicable separate from the one genuine consumer program and reject truncated or changed samples.

验证：新事务 `libwpg-ci-repair-w3-20261013-r1` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `dc8e1403b14e5241d94a7c523bb6d29f4c1bf93352f35357e350a7445dc1c42a`。上游声明 0 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。


## 2026-10-13 CI 反例与修复增量

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

Current worker logs provide the independent second-failure boundary after the earlier checkout/fixture repair: successful source retrieval and dependency installation are not proof that configure generated usable config files. Use both-branch source reconciliation, timestamp-preserving production-helper tests and complete native recipe/tests; do not treat a missing-curl predownload warning as the cause when source() already succeeded. This extends the existing evidence/transport topic with a causal validation boundary, not a new generic umask claim.

验证：新事务 `libwpg-ci-repair-w3-20261013-r101` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `3feea958cb63877cd9f3feb927de09d3bb6f40511f156662593897ce00ab2fcd`。上游声明 0 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。
