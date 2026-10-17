# DRAFT-windows-msys-path-mangling-and-invalid-filename-worktree-checkout：Windows/Git-Bash 双坑——MSYS 路径转换弄坏 sparse-checkout 模式；上游含非法文件名导致 worktree 检出失败

> Status: **Draft**（待审核 promote）| severity: `P2` | category: `platform` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-windows-msys-path-mangling-and-invalid-filename-worktree-checkout.kv`

---

**匹配关键词**：worktree add 失败, Invalid argument, unable to create file, sparse-checkout, MSYS 路径转换, Git Bash, \r 文件名

## 错误签名（error_signature）

```text
git worktree add: error: unable to create file <路径>??: Invalid argument
                  fatal: Could not reset index file to revision 'HEAD'
git sparse-checkout list 输出形如：!C:/Program Files/Git/<本应排除的路径>/
```

## 错误摘录（error_excerpt）

```text
error: unable to create file archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??: Invalid argument
```
（`??` 处是文件名里的 \r\r；Windows API 禁止文件名含控制字符，任何 checkout 都
无法在 NT 工作区实体化该文件）

## 根因（root_cause）

两个独立但常叠加的 Windows 坑：

1. **仓库里有文件名含 \r 等控制字符的文件**（Linux 端合法、Windows 非法）：
   `git worktree add` 检出 97k 文件到 29% 时报 Invalid argument，整个 worktree
   回滚；主工作区则表现为该文件永远处于"已删除"状态。
2. **Git Bash 的 MSYS 路径转换**：`git sparse-checkout set --no-cone '/*'
   '!/archives/g/gama/'` 里的 `/archives/...` 被自动改写成
   `C:/Program Files/Git/archives/...`，排除规则完全失效（git status 依旧报该
   文件 deleted），且无任何告警。

## 推荐方案（rec_approach）

```sh
# 1) 绕过非法文件名：先建 worktree 不检出，再用 sparse-checkout 排除该目录
git -C <主仓库> worktree add --no-checkout -b <分支> <worktree路径> origin/main
cd <worktree路径>
printf '/*\n!/archives/g/gama/\n' > "$(git rev-parse --git-dir)/info/sparse-checkout"
git sparse-checkout reapply && git checkout <分支>
# 注意：worktree 的 .git 是文件不是目录，配置要写到主仓库 .git/worktrees/<名>/info/ 下
# （git rev-parse --git-dir 会给真实路径）

# 2) 防 MSYS 路径转换：凡是要给 git 传以 / 开头的模式/路径参数，
#    要么 MSYS_NO_PATHCONV=1 前置，要么（如上）直接写文件绕开命令行参数。
```

识别信号：checkout 中途 `Invalid argument` + 文件名尾部 `??`；或
sparse-checkout list 里出现 `C:/Program Files/Git/...` 前缀。

## 复用价值

所有在 Windows 上建 worktree 适配本仓库的会话都会撞上（gama 这个文件在
origin/main 长期存在）；两步修复让 worktree 状态干净（不再显示 deleted），
避免误提交。图谱查重 0 命中（2026-09-27：sparse-checkout / MSYS / Invalid
argument + worktree 均无条目）。
