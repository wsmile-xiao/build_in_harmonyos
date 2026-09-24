# DRAFT-patch-autotools-ohos-sub-kernel-guard-order：patch-autotools-ohos.pl 的 §2.3 守卫 `unless ($sc =~ /linux-ohos/)` 在 §2.1 先写入 basic_os=linux-ohos 后恒为真，导致 config.sub 内核-OS 校验列表未补 linux-ohos*，三元组仍被拒

> Status: **Draft**（待审核 promote）| severity: `2` | category: `autotools|configure|tooling` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-patch-autotools-ohos-sub-kernel-guard-order.kv`

---

## 触发面

- trigger_tool: `perl / patch-autotools-ohos.pl / config.sub`
- phase: `configuration`

**匹配关键词**：patch-autotools-ohos.pl, linux-ohos, config.sub, kernel-os validation, not known to work, guard order, basic_os=linux-ohos

## 错误签名（error_signature）

```text
Kernel .linux. not known to work with OS .ohos.|Invalid configuration .*linux-ohos.*not known|config.sub.*not known to work
```

## 根因（root_cause）

脚本执行顺序为 §2.1（插入 `ohos-linux)` 分支，其中含字符串 `basic_os=linux-ohos`）→ §2.3（守卫 `unless ($sc =~ /linux-ohos/)` 期望检测 “内核校验列表是否已含 linux-ohos”，但此时文件已因 §2.1 含该子串）→ 守卫恒真 → 跳过。结果：config.guess 输出 aarch64-unknown-linux-ohos、config.sub 接受 `ohos-linux` 与 `ohos*`，但在最后的 `case $kernel-$os` 校验处以 `Kernel \`linux' not known to work with OS \`ohos'` 退出（exit 1）。

## 推荐方案（rec_approach: `fix-tool-guard-scope`）


## 验证方式（verification）

```text
libnfsidmap-ldap/2.6.4 实证：脚本输出 `[skip] linux-ohos already present` 后 `sh ./config.sub aarch64-unknown-linux-ohos` → `Invalid configuration ... Kernel \`linux' not known to work with OS \`ohos'`（exit 1）； 按 E122 手工补 `| linux-ohos*` 后 → `aarch64-unknown-linux-ohos`（exit 0）， configure 输出 `checking build system type... aarch64-unknown-linux-ohos` （2026-09-15）。
```

## 补充关键词

官方补丁脚本缺陷, 守卫顺序, linux-ohos 内核校验, config.sub 三元组被拒

## 关联

- **关联**：E007（config.guess/sub OHOS 补丁总入口）、E072（config.sub 三元组验证失败）、 E122（linux-ohos 内核校验列表）——本条是三者共同作用下的工具链缺陷。

---

*本文件由 `knowledge/drafts/DRAFT-patch-autotools-ohos-sub-kernel-guard-order.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
