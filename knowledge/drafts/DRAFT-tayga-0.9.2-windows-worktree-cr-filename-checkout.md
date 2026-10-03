# DRAFT — Windows 上 worktree add 因上游 \r 文件名检出失败

> Status: **Draft**（待审核 promote）｜ severity: `2` | category: `platform|git|filesystem|workflow` | Updated: 2026-10-01
> 对应: `knowledge/drafts/DRAFT-tayga-0.9.2-windows-worktree-cr-filename-checkout.kv`

## 错误签名

```text
fatal: Could not reset index file to revision 'HEAD'.
error: unable to create file archives/g/gama/2.29/patches/0002-dataparser-ungated.patch<CR><CR>: Invalid argument
```

## 触发场景

Windows 上按"一库一分支"流程从 origin/main 新建 worktree：

```powershell
git worktree add -b feat/<lib>-<ver>-codex D:\harmonyos\worktrees\<lib> origin/main
```

全部文件 `Updating files: 100%` 完成后，在写 index 一步失败并自动回滚删除 worktree 目录。重试、`-c core.fscache=false`、预创建目录均无效。

## 根因

origin/main 历史提交里有文件名以双 `\r` 结尾的文件（实例：`archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r`）。Windows 文件系统禁止文件名含 CR 控制字符，`CreateFile` 报 `Invalid argument`，index 写入随之失败。主工作区能存活只是因为该文件长期处于 deleted 状态（`git status` 显示 `D "…patch\r\r"`，引号包裹 + 不可见字符）。这是仓库内容与 Windows 的不兼容，与 config.guess 三元组问题（E007/E122）无关。

## 推荐方案（no-checkout + sparse-checkout 绕行）

```powershell
# ① 只建元数据不检出
git -C <repo> worktree add --no-checkout -b feat/<lib>-<ver>-codex <wt> origin/main
# ② 启用非 cone 稀疏检出
git -C <wt> sparse-checkout init --no-cone
# ③ 写排除规则（\r 用实际控制字符；也可用目录级排除更省事）
#    文件：<repo>/.git/worktrees/<name>/info/sparse-checkout
#    内容：
#    /*
#    !/archives/g/gama/2.29/patches/
# ④ 检出
git -C <wt> checkout
# ⑤ 防误提交删除
git -C <wt> update-index --skip-worktree "archives/g/gama/2.29/patches/0002-dataparser-ungated.patch`r`r"
```

## 验证

`git -C <wt> status --short --branch` 应只剩正常内容；`git diff --name-only origin/main...HEAD` 只含自己库目录。排除无关路径不违反"只改自己库目录"的交付边界。

## 来源

tayga/0.9.2 适配（2026-10-01）：首次为本库建 worktree 时连续三次失败，GIT_TRACE 定位到 Invalid argument 行。

---
*本文由 `knowledge/drafts/DRAFT-tayga-0.9.2-windows-worktree-cr-filename-checkout.kv` 字段衍生（补齐 kv→md 配套）；与 dmc_unrar 的 sparse-checkout 草稿根因不同（那是 HMDFS inode ENOSPC，这是 Windows CR 文件名）。*
