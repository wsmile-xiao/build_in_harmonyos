# DRAFT-parse-1.22.2-sparse-checkout-worktree-inode：inode 受限共享文件系统上 git worktree 完整 checkout 失败——--no-checkout 骨架 + sparse-checkout cone 只物化必要路径

> Contributor: pc1-15 | Status: Draft | Updated: 2026-09-21
> Source: parse 1.22.2 适配（Path B 知识库扩展）R01 worktree 创建（feat/parse-1.22.2）
> 对应：`knowledge/drafts/DRAFT-parse-1.22.2-sparse-checkout-worktree-inode.kv`

## 现象

`git worktree add -b feat/parse-1.22.2 <path> origin/main` 失败：

```text
Preparing worktree (new branch 'feat/parse-1.22.2')
error: unable to create file archives/k/knewstuff/6.14.0/notes.md
fatal: cannot create directory at 'archives/k/knewstuff/6.14.0/patches'
EXIT:128
```

重试后失败路径漂移（libupnpp、liburcu……），`df -h` 块空间仍充足
（928G/66%）——这是 **inode 耗尽**（`df -i` IUse%=100%，剩余 <8 万
inode），不是磁盘满。分支被部分创建（refs/heads/feat/parse-1.22.2
残留指向 origin/main），但 worktree 目录未物化。

## 根因

worker 共享分布式文件系统（HMDFS）inode 池**全局共享且 100% 水位**。
本仓库 ~4.1 万跟踪文件 + HMDFS 每文件多 inode 开销 + 230+ 个既有
worktree（每个都是全量 checkout）把 inode 池占满。`git worktree add`
默认完整 checkout 全部文件，需要一次性创建数万 inode，超过剩余预算，
必在某个目录创建点失败；失败路径逐轮漂移正说明是总量约束而非某个
特定文件问题。

## 修复（已验证）

四步规避全量 checkout 的 inode 需求：

```bash
# 1) 只建骨架（.git 元数据 + 目录，inode 开销极小）
git worktree add --no-checkout /storage/Users/currentUser/junshi_liu/worktrees/parse-1.22.2 feat/parse-1.22.2

# 2) 启用 cone 稀疏检出
git sparse-checkout init --cone

# 3) 只注册流程必要目录（当前库归档 + 流程依赖）
git sparse-checkout set archives/p/parse knowledge scripts templates ci references docs feedback

# 4) 加载 index 并物化文件
git read-tree HEAD
git sparse-checkout reapply
```

结果：分支唯一（`git worktree list --porcelain` 单匹配
feat/parse-1.22.2）、HEAD=42a8cc8（==origin/main）、磁盘物化 4153 文件
（全量 4.1 万的 1/10）、`git status` 干净。后续 W2/W3/finish/submit 依赖
的 knowledge/scripts/ci/templates 均在 cone 内可用。

**注意**：稀疏检出下 cone 外路径会显示为 D（删除）状态属正常现象；
`sparse-checkout reapply` 物化后工作区文件数正确、status 干净即为成功。

## 适用范围

大仓库（数万文件）+ inode 受限共享文件系统 worker 上创建任何新库专用
worktree 的通用手法；同一 worker 上所有新库 R01 均适用（本仓库 230+
worktree 共存场景）。

## 边界 / 反例

- 若后续流程需要全仓文件（如整仓审计），cone 外路径不可读——需按需把
  目录加进 `sparse-checkout set` 或用 fallback 先释放 inode 再完整 checkout
- 仅当确认是 inode 耗尽（`df -i` 100%）且块空间充足时才走稀疏方案；
  块空间真满时需清理大文件
- 禁止在他人 worktree 内 checkout 切分支绕过创建（任务约束：专属 worktree）

## 关系

- caused_by / similar_to: DRAFT-shared-fs-inode-exhaustion（inode 诊断与错峰）
- similar_to: E497（HMDFS worktree git 元数据）、
  DRAFT-astronomy-2.1.9-upstream-test-data-external-repo-drift（git sparse clone 上游数据，场景不同）
- 适用原则: W1（同步 main）、W2（PR 原子性）
