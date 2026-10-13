# 鸿蒙PC hmdfs 先耗尽 inode：worktree 全量检出中途随机失败

> Draft: `DRAFT-TUPTIME-525-HMDFS-INODE-EXHAUSTION-WORKTREE`
> Stem: `tuptime-5.2.5-hmdfs-inode-exhaustion-worktree` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-TUPTIME-525-HMDFS-INODE-EXHAUSTION-WORKTREE
- **严重度**: 2
- **类别**: platform|tooling
- **触发工具**: git|manual
- **阶段**: setup

## 现象

```console
$ git worktree add "$WT" -b feat/tuptime-5.2.5 origin/main
Updating files:  18% (20593/112969)
error: unable to create file archives/d/dawn/0.0-git20260529.432db5d7/test_package/test.c
fatal: cannot create directory at 'archives/d/dazz_db'
```

**重试会在完全不同的路径失败**（首次是 `archives/g/gcc-ada/...`），
看起来像磁盘满或文件系统抖动 —— 其实不是。

## 根因：inode 枯竭，不是空间

```console
$ df -h /storage/Users/currentUser
# 928G total / 194G avail —— 空间充足，且 df 不显示 inode

$ stat -f -c "blocks=%b free=%f avail=%a files=%c ffree=%d" /storage/Users/currentUser
blocks=243207761 free=50967804 avail=50935036 files=48455677 ffree=85133
                                                  ^^^^^^^^^^^^^^^^^^
                                                  空闲 inode 仅 85,133

$ git -C <repo> ls-files | wc -l
88718      # 受跟踪文件 88,718（archives/ 占 84,030）
```

要检出的文件数（88,718）> 空闲 inode 数（85,133），所以必然中途 inode 用尽。
失败点取决于当时的 inode 余量 → "随机路径失败"的假象。

## 推荐方案

**方法**: `use-sparse-checkout-worktree`

```console
$ stat -f -c "files=%c ffree=%d" /storage/Users/currentUser   # 先查 inode
$ git worktree add --no-checkout "$WT" feat/tuptime-5.2.5 origin/main
$ git -C "$WT" sparse-checkout init --cone
$ git -C "$WT" sparse-checkout set archives/t scripts ci knowledge templates \
      config docs references tests code probes feedback .gitcode
$ git -C "$WT" checkout
```

- 结果：**10,834 个文件** vs 全量 ~113,000，远低于 inode 余量。
- 新增文件不受 sparse 影响（untracked 照常 `git add`）。
- 不要用 `git clone --depth 1` 绕（同样物化全部工作区文件，inode 照样爆）。
- 不要删他人的 worktree 去腾 inode。

## 验证命令

```bash
stat -f -c "files=%c ffree=%d" /storage/Users/currentUser
find "$WT" -type f | wc -l
```

## 取证记录

- 复现 2 次（不同失败路径），随后稀疏检出成功
- 日志：本任务 worktree `/storage/Users/currentUser/Desktop/lan workspace/tuptime-5.2.5-wt`
