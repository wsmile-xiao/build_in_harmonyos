# DRAFT: HMDFS 大小写不敏感 + git —— 大小写变体目录冲突使工作区恒报“已修改”

- **草稿 ID**: DRAFT-E546-hmdfs-case-insensitive-git-case-variant-dir-collision
- **来源**: build_in_harmonyos 工作区实测（`archives/l/libXext` 与 `archives/l/libxext` 并存）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **同族条目**: E046（HMDFS 下 chmod 不生效）

## 错误特征

工作区**恒**报告非本任务的文件被修改（内容与 HEAD 不同，但没有任何人编辑它）：

```
$ git status --porcelain
 M archives/l/libXext/README.md
 M archives/l/libXext/manifest.yaml
$ git config --get core.ignorecase
true
```

## 触发条件

- 文件系统: OHOS **HMDFS**（大小写不敏感，git 探测 `core.ignorecase=true`）
- 仓库同时跟踪两个**仅大小写不同**的路径，例如：
  - `archives/l/libXext/manifest.yaml`（blob `863136da…`）
  - `archives/l/libxext/manifest.yaml`（blob `f85a944d…`）
- 阶段: 任意（`git status` / PR 原子性审计）

## 根因分析

大小写不敏感 FS 上，`libXext/` 与 `libxext/` 落在**同一物理文件**上，只能保留一份 blob 内容；git 的另一条路径因而恒判 `M`。这与任务内容无关，且**每个 worktree 一致出现**——会把 W2 文件归属/原子性审计误导为“混入了他包改动”。

```
$ git ls-files | grep -i xext
archives/l/libXext/README.md
archives/l/libXext/manifest.yaml
archives/l/libxext/1.3.6/manifest.yaml
archives/l/libxext/1.3.7/conanfile.py
...
$ git show HEAD:archives/l/libXext/manifest.yaml | sha256sum   # 863136da…
$ sha256sum archives/l/libXext/manifest.yaml                   # f85a944d…（= lowercase 变体 blob）
```

## 解决方案

### 推荐方案：把冲突路径排除出变更集（本地索引标记，不改内容）

```bash
git update-index --skip-worktree archives/l/libXext/README.md archives/l/libXext/manifest.yaml
git add archives/r/<pkg>/          # 精确只入本包，保证单软件原子性
git status --porcelain            # 之后仅显示本包变更
```

`--skip-worktree` 仅存于本 worktree 的索引，不改文件内容、不入库、不影响主工作区；审计/门禁以 **prdiff**（只扫 PR 变更文件）为准即可。

### 回退方案

不改索引标记，直接以 PR 变更文件集做门禁：

```bash
JUNK_PR_DIFF=<pr.diff> bash ci/scripts/junk_check.sh   # CHECK_FILES 取自 pr.diff，避免 full 模式全仓扫描误报
```

### 禁止做法

- ❌ `git checkout -f` / `git clean -fd` / `rm -rf archives/l/libXext` —— 会丢弃同 worktree 他人未提交改动；且大小写变体的内容选择会翻转，下次审计改报另一条。
- ❌ `git add -A` / `git commit -a` —— 会把冲突路径（他包）一并入册，破坏 PR 单软件原子性。

## 验证

```bash
git ls-files -v -- archives/l/libXext/README.md archives/l/libXext/manifest.yaml   # → 以 "S " 开头（skip-worktree）
sha256sum archives/l/libXext/manifest.yaml                                        # → 内容未变（f85a944d…）
git status --porcelain                                                            # → 仅本包变更
```

## 关联条目

- 相关: E046（HMDFS chmod 不生效）、E011/E112（HMDFS 临时目录/umask）
