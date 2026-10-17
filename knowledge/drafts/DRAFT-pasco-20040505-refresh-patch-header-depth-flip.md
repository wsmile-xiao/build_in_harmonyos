# DRAFT: refresh-patch 重生成时补丁头路径深度会翻转，并覆盖上一轮已正确的补丁

- **触发实例**：pasco 20040505 适配（任务 #9321，构建机 B，2026-09-27，worktree `~/qzy/主理-74-pasco-20040505`）
- **错误签名**：`Apply patch ... Hunk FAILED` / `source/target file does not exist:`（`-p1` 打不到 `src/Makefile`）
- **类别**：tooling, conan, patch, harness
- **严重度**：2（会把已正确的交付补丁静默改坏，修复动作固定且必须在让渡前完成）

## 症状

pasco 上游（ODESSA/pasco）只带 `src/Makefile`，没有 configure/CMake。适配过程中同一枚
`patches/0001-Makefile.patch` 的**头两行路径深度来回变了三次**，且每次 `refresh-patch`
（含 `finish` 内部的自动重生成）都会把前一枚备份掉：

```text
# 一手读数：三枚工具备份（已移出 worktree，落在 ~/tmp/uc2/z74-pasco-w4/backups/）
.patch-backup-20260927005738/0001-Makefile.patch  414 B  --- a/Makefile      +++ b/Makefile
.patch-backup-20260927015042/0001-Makefile.patch  456 B  --- a/src/Makefile  +++ b/src/Makefile   ← 正确
.patch-backup-20260927015147/0001-Makefile.patch  448 B  --- a/Makefile      +++ b/Makefile      ← 又被压平
# 交付态（HEAD 00a84ae214）
archives/p/pasco/20040505/patches/0001-Makefile.patch    --- a/src/Makefile  +++ b/src/Makefile
```

两枚只差头的备份 **456 B vs 448 B = 8 B**，正好等于两行头各插入 `src/`（4 字符 ×2 行）
⇒ 这一对备份之间除路径深度外无其它差异，头翻转是唯一变量。

## 根因

`refresh-patch` 用「探索目录（工作副本）vs `.orig`」两棵树做 diff 生成补丁，**头里的路径前缀
取自探索目录当时的相对布局**，而不是取自 `conandata.yml` 里目标 tarball 的真实布局。
于是：

- 探索目录被压平（`Makefile` 放在根）⇒ 生成 `--- a/Makefile`，`apply_conandata_patches` 以
  `-p1` 应用时打不到 `src/Makefile`；
- 探索目录与目标树同构（有 `src/` 层）⇒ 生成 `--- a/src/Makefile`，正确。

两种布局在同一次任务里被切换过（01:48 生成正确、01:50 再生成又压平），**最后一次决定交付态**
⇒ 该缺陷不是"一次性写错"，而是非幂等：只要盘外探索目录布局不对，重跑 `finish` 就会复现。

## 解决方案

1. **探索目录与目标树同构**：目标文件在 `src/Makefile`，探索目录里也必须建 `src/` 层，
   ⛔ 把文件压平放在探索目录根上去"省一层"。
2. **让渡前硬动作**：每次 `finish`（内部含 refresh-patch 重生成）之后复验头，与目标树实际路径逐字对：
   ```bash
   head -2 archives/p/pasco/20040505/patches/*.patch      # 须是 --- a/src/Makefile / +++ b/src/Makefile
   ```
3. 头错时**按同构布局重新生成**，⛔ 只手改两头了事 —— 手改的那一枚会被下一次 `finish` 再覆盖。
4. `patches/` 里的 `.patch-backup-<时间戳>` 是**目录**且不被 `.gitignore` 覆盖 ⇒ 收口前必须
   ```bash
   git ls-files -o --exclude-standard -- archives/<l>/<pkg> | wc -l      # 须为 0
   ```
   非 0 就把备份**移出 worktree**（⛔ 就地删除），否则 `git add <归档目录>` 会把它们折进 PR。

## 与既有条目的区别

| 对比项 | `DRAFT-LIBFEC-REFRESH-PATCH-HMDFS-DRYRUN-PLACEHOLDER` | 本条 |
|---|---|---|
| 触发工具 | 同为 `refresh-patch --auto` | 同为 `refresh-patch`/`finish` |
| 错误签名串 | `source/target file does not exist:` —— 与本条**字面同串** | 同串，但成因不同 |
| 成因 | HMDFS 上 `patch --dry-run` 真实创建 0 字节占位文件 ⇒ **"新增文件"被误判为"修改文件"** ⇒ 头变成 `--- a/<file>`（新增文件必须 `--- /dev/null`） | 目标文件**本来就存在**，头的前缀取自**盘外探索目录的相对布局** ⇒ 路径**深度**在 `a/` 与 `a/src/` 之间翻转 |
| 处方 | 每轮前删 `.orig` 里的 0 字节占位，使新增文件恒以 `--- /dev/null` 生成 | 探索目录与目标树同构 + 让渡前复验 `head -2` + 错时重生成而非手改头 |
| 适用边界 | 其 `affected_scope` 明限于"orig 中不存在的**新增源文件**" | 本条恰是**已存在文件**，落在其 scope 之外 |

⇒ 症状串同形而**因与处方均不同一条**，且既有条目的边界不排除本情形（本情形在其边界之外）。
另注：`knowledge/drafts/` 内以 `补丁头` 检索命中 41 处/18 个文件，逐条读后无一命中"探索目录布局
不同构导致头深度翻转"这一成因（第二读：W4 r1 审计棒独立检索）。

## 验证

```bash
# ① 交付态头路径深度与目标树一致（pasco 目标树只有 src/Makefile）
head -2 archives/p/pasco/20040505/patches/0001-Makefile.patch
# ② 归档目录内无未跟踪未忽略的工具备份件
git ls-files -o --exclude-standard -- archives/p/pasco | wc -l        # 期望 0
# ③ 复现性判据：把探索目录压平再跑一次 finish，若头退回 a/Makefile 即命中本条
```

本包实测：①为 `--- a/src/Makefile`/`+++ b/src/Makefile`；②整改后为 0（三枚备份移至
`~/tmp/uc2/z74-pasco-w4/backups/`）；③由 01:48→01:50 两枚备份的翻转一手坐实。
