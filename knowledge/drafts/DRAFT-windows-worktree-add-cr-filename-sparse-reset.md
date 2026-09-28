# DRAFT-windows-worktree-add: Windows 上从 origin/main 创建 worktree 的连环坑——CR 文件名检出必败 + 继承主仓 index 的幽灵修改

> 来源:eta 1.0.1 适配会话(2026-09-27)。两个坑在同一次 `git worktree add` 流程中先后出现,已验证出完整安全配方。

## 症状一:worktree add 在 100% 处失败并被回滚

```text
Updating files: 100% (97107/97107), done.
error: unable to create file archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??: Invalid argument
fatal: Could not reset index file to revision 'HEAD'.
```

- 检出 97107 个文件走到 100% 仍失败,worktree 目录被 git 自动删除(`git status` 报 No such file or directory)。
- 主仓工作区里同一路径**永远显示为已删除**(D),这是同一个问题的另一面。

## 根因一

origin/main 里有一个**文件名以两个回车符(0x0D 0x0D)结尾**的提交文件:

```sh
git ls-tree origin/main -- archives/g/gama/2.29/patches/ | cat -A
# "archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r"
```

Windows Win32 API 禁止文件名包含控制字符(0x00–0x1F),任何对该提交的完整检出在 Windows 上**必然**在创建这个文件时失败,`core.protectNTFS` 等配置救不了。Linux 端不受影响——所以 CI 正常、Windows 协作者全灭。

## 症状二:`--no-checkout` 重建后出现「幽灵修改」

按常规用 `--no-checkout` + 稀疏检出重建 worktree 后,`git status` 在**全新目录**里显示:

- 大量 `D` 条目(index 有、盘上无);
- 物化出来的文件内容是**主仓工作区的暂存内容**(实测某包 README.md 的内容哈希等于主仓已暂存 blob,而非分支提交版本)。

## 根因二

`git worktree add` 会以当前仓库的 index 作为新 worktree 的初始 index——主仓 index 里带着 **skip-worktree 位**(Windows 上无法检出的文件都被打了位)和**已暂存的用户改动**。后续 `read-tree -mu` 在部分条目上复用这些旧条目,把主仓的工作区状态"渗透"进新 worktree。

## 安全配方(已全流程验证)

```sh
REPO=D:/harmonyos/build_in_harmonyos
LIB=<库名>
git -C "$REPO" worktree add --no-checkout -b "feat/$LIB-<版本>-codex" "D:/harmonyos/worktrees/$LIB" origin/main

# 1. 直接写稀疏模式文件(不要经 git sparse-checkout set 传参,见下方 MSYS 坑)
GD="$REPO/.git/worktrees/$LIB/info/sparse-checkout"
printf '/*\n!/archives/\n/archives/%s/%s/\n' <首字母> "$LIB" > "$GD"
git -C "$REPO" config --worktree core.sparseCheckout true   # 若尚未开启

# 2. 关键:--reset 丢弃继承来的主仓 index,按稀疏模式重新物化
git -C "D:/harmonyos/worktrees/$LIB" read-tree -u --reset HEAD

# 3. 铁律:动工前 status 必须为空
git -C "D:/harmonyos/worktrees/$LIB" status --short   # 期望:无任何输出
```

要点:

- 稀疏排除 `archives/`(97k 文件的 95%,顺带绕开坏文件名),再**回纳自己的包目录**;排除区内新建文件可正常 `git add`(包目录回纳后连 `--sparse` 都不需要)。
- **MSYS 坑**:Git Bash 会把 `git sparse-checkout set '/*' '!/archives/'` 的第二个参数改写成 `!C:/Program Files/Git/archives/`,排除模式静默失效。要么 `MSYS_NO_PATHCONV=1`,要么像上面一样直接 printf 写文件并 `cat` 复核。
- `read-tree` 参数是 `-u --reset HEAD`,`-mu --reset` 会报 `Which one? -m, --reset, or --prefix?`。
- 步骤 3 若非空(尤其出现与主仓暂存内容一致的字节),立即删 worktree 重建,**不要带病开工**。

## 复用面

任何 Windows 协作者在当前 main(带着坏文件名)上开新 worktree 都会踩症状一;任何以「复制 index 加速」路径创建的 worktree 都可能踩症状二。长期正解是从仓库侧清理那个 CR 文件名(Linux 端 `git mv` 改名),本配方是清理前的可用绕行。
