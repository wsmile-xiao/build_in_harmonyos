# DRAFT-windows-worktree-cr-filename：origin/main 树上含 CR 字符文件名，Windows 检出 worktree 必败（Invalid argument），--no-checkout + sparse-checkout 排除绕过

> Draft（未 promote）— 来源于 fathom 1.0 适配建 worktree（2026-09-27 实证）
> 对应 `.kv` 文件同 stem：`DRAFT-windows-worktree-cr-filename-invalid-argument.kv`

## 症状

在 Windows（NTFS，Git Bash 的 git）上从最新 origin/main 建 worktree：

```sh
git worktree add -b feat/<库>-<版本> /d/harmonyos/worktrees/<库> origin/main
```

检出推进到 `archives/g/` 段（约 28%）时中断：

```
error: unable to create file archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??: Invalid argument
fatal: Could not reset index file to revision 'HEAD'.
```

重试永远在同一文件失败。主工作区 `git status` 里那条一直存在的
` D "archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r"`
就是同一根源的另一种表现（旧基线检不出该文件，被记成删除）。

## 根因

`git ls-tree origin/main -- archives/g/gama/2.29/patches/` 可见树对象里
有一个文件名以**两个 CR（\r\r）结尾**的 blob（git 输出带引号转义
`"0002-dataparser-ungated.patch\r\r"`）。NTFS 文件名不允许 0x00–0x1F 控制
字符，Windows API 创建时报 `Invalid argument`。这是上游某次提交把带 CR 的
文件名合进了树，**任何 Windows 机器全量检出最新 main 都会失败**，与磁盘、
权限、git 版本无关。

## 方案

worktree 是本地工作区过滤，sparse-checkout 排除不改变提交树内容，push/PR
不受影响：

```sh
# 1) 建 worktree 但先不检出
git -C <主仓库> worktree add --no-checkout -b feat/<库>-<版本> \
  <worktree 路径> origin/main

# 2) 排除含损坏文件名的目录（no-cone 模式，gitignore 风格）
git -C <worktree> sparse-checkout set --no-cone '/*' '!archives/g/gama/2.29/patches/'

# 3) 完成检出
git -C <worktree> checkout
```

完成后 `git status` 中该文件不再出现（被 skip-worktree 覆盖）。

## 三个连带陷阱（同一会话实证）

1. **MSYS 路径转换吃掉模式里的前导 `/`**：在 Git Bash 里写
   `sparse-checkout set '/*' '!/archives/g/gama/2.29/patches/'`，第二个模式
   的 `!/archives/...` 会被 MSYS 转成 `!C:/Program Files/Git/archives/...`
   写进配置（静默失效）。模式一律**不要以 `/` 开头**（含内部 `/` 即锚定根），
   或加 `MSYS_NO_PATHCONV=1`。同类：`grep -v '/'` 的模式也被转换成无意义
   路径——用 `awk -F/ 'NF==1'` 之类替代。
2. **大小写变体目录互相覆盖**：仓库同时有 `archives/l/libXext/` 与
   `libxext/`，在不区分大小写的文件系统上检出互相覆盖，`git status` 常驻
   两条伪 ` M`（repo 提交 7f618b00ee 即为此问题的同步记录）。**建 worktree
   前先 `git ls-tree origin/main --name-only archives/<首字母>/ | grep -i <库>`
   确认无大小写变体**；提交时用显式 pathspec（如 `git add archives/f/fathom`）
   避免把伪差异带进 PR。
3. **失败的 worktree add 会留下空目录与分支**：重试前
   `git worktree prune` + `git branch -D <分支>`（或先 `worktree list` 核对）。

## 复用价值

所有在 Windows 侧从最新 main 建 worktree 的适配者都会撞上；无需等上游修复
文件名即可继续并行适配。
