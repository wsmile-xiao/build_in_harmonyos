# Windows 主机 worktree 检出被仓库内含字面 `\r` 文件名的 blob 阻断：用 --no-checkout + sparse-checkout 排除规避

- **软件**: libltc 1.3.2（泛化到所有在 Windows 本机开 worktree 的库适配）
- **阶段**: bootstrap（`git worktree add`）
- **severity**: 2
- **状态**: DRAFT

## 现象

```
error: unable to create file archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r: Invalid argument
fatal: Could not reset index file to revision 'HEAD'.
```

`git worktree add` 全量 checkout 到 100% 后报 Invalid argument 并 fatal；
`git ls-tree origin/main "archives/g/gama/2.29/patches/"` 可见一个文件名含
**字面 `\r\r`（两个回车字符）** 的空 blob（e69de29...）。worktree 目录留下半成品
（有文件但无 .git），`git status` 报 "not a git repository"。

## 根因

Windows 文件系统禁止文件名包含 0x00-0x1F 控制字符，`\r`（0x0D）在其中。
只要 origin/main 的历史里存在这种 blob，**任何 Windows 上的全量 checkout 都必然失败**，
与当前适配的库无关（libltc 只是恰好撞上）。Linux/HMDFS 端不受影响。

## 修复（实测通过）

```powershell
# 1) 清掉半成品（目录 + 分支 + 注册）
Remove-Item -Recurse -Force D:\harmonyos\worktrees\<库名>
git -C <主仓库> branch -D <分支名>; git -C <主仓库> worktree prune

# 2) --no-checkout 创建 + sparse-checkout 排除坏路径所在目录
git -C <主仓库> worktree add --no-checkout -b feat/<库>-<版本> <worktree路径> origin/main
# sparse 文件写到主仓库 gitdir 下的 worktree 私有区：
#   <主仓库>\.git\worktrees\<库名>\info\sparse-checkout
#   内容两行：/*  和  !archives/g/gama/     （排除整个 gama 目录即可，与当前库无关）
git -C <worktree> config core.sparseCheckout true
git -C <worktree> reset --hard HEAD
git -C <worktree> switch -c <分支名>   # 若 add 时分支创建被跳过
```

注意：
- sparse 文件路径在**主仓库的 .git\worktrees\<名>\info\**，不是 worktree 自身目录。
- 排除粒度取"坏文件所在的最小无关目录"（gama 与本库无关，整目录排除最稳）。
- 提交/push 不受 sparse 影响（被排除文件未改动）；但该 worktree 上不能做涉及该目录的改动。

## 证据

libltc 1.3.2 适配（2026-09-29）：按上述流程在 Windows 建立
`D:\harmonyos\worktrees\libltc`（feat/libltc-1.3.2-codex @ origin/main 317e16ed5a），
后续配方编写、PR 提交（atomgit PR #13721）全部正常；
`git status` 仅显示两个 libXext 文件的 CRLF 噪音（不提交即可）。

## 关联

- 与 DRAFT-dmc_unrar-1.8.0-hmdfs-inode-enospc-sparse-checkout 互补：
  那条是 HMDFS inode 耗尽（设备端），本条是 NTFS 文件名字符集（Windows 端），
  解法同为 sparse-checkout 但触发面完全不同。
- 长期修复应由基础设施侧删除/改名该 blob（需单独 PR，不混入库适配 PR）。
