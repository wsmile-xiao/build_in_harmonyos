# DRAFT: HMFS security.* xattr 不可读时跳过而非中止 — composefs 1.0.8 适配实证

## 问题
composefs `mkcomposefs` 在 HMFS 上扫描目录报 `error accessing <path>: Invalid argument`。
精确定位：`read_xattrs`（lcfs-writer.c:479）对 `listxattr` 列出的每个条目逐个 `getxattr`，
而 HMFS 目录的 `listxattr` 暴露 **security.hmmac**（及 security.selinux），非特权用户
`getxattr(security.hmmac)` 失败（EACCES/EINVAL/EPERM 族），任意失败即整体中止目录扫描。

## 根因
HMFS 内核托管 security.hmmac 属性，列表可见但不可读（无 root 权限语义）；这些属性是
文件系统内部元数据，不携带可跨文件系统迁移的业务语义。composefs 未区分"单条目不可读"
与"读属性机制损坏"，把前者当后者处理。

## 方案
最小补丁（read_xattrs）：getxattr 失败时，若条目以 `security.` 开头且
`errno ∈ {EACCES, EINVAL, EPERM}`，`continue` 跳过该条目；其余属性按原逻辑读取。
语义：内核托管的 security.* 不可读即不迁移（与按条目粒度的 skip-xattrs 等效）。

## 验证（本轮真实日志）
- 探针：HMFS 目录 `listxattr` → [security.hmmac, security.selinux]；`getxattr(security.hmmac)` 失败
- 补丁后：`mkcomposefs` 对含 security.* 的目录构建成功；`check-units` test_inline/test_objects PASS

## 适用边界
- 适用：OHOS HMFS 上"listxattr→逐条 getxattr 读拷贝"的工具（composefs、备份/归档类）
- 反例：不可把整体 xattr 读取丢弃（-Dskip-xattrs 全局开关）——会丢失 user.*/security.capability
  等可迁移属性；security.* 中 security.capability 若可读仍应保留

## 查重差异（七轴摘要）
| 轴 | 结论 |
|---|---|
| exact_duplicate | 否（无同名条目） |
| causal_duplicate | 与 DRAFT-tar-1.35-hmdfs-dir-xattr-einval **根因相同**（HMFS security.hmmac 列表可见但不可读） |
| trigger_overlap | 部分（tar 是"读失败→平台限制报告"；本候选是"构建工具扫描中止"） |
| solution_overlap | 无（tar 方案=迁移到 POSIX fs；本方案=工具内跳过条目，工具可在 HMFS 正常工作） |
| combination_novelty | 是（跳过粒度 + 保留其余属性的组合） |
| boundary_novelty | 是（"单条目跳过"边界，安全保留可读 security.*） |
| test_migration_novelty | 是（check-units 实测迁移） |

关系：similar_to=DRAFT-tar-1.35-hmdfs-dir-xattr-einval；无 prerequisite/conflicts。
