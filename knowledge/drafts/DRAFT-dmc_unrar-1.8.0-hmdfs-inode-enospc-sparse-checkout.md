# DRAFT-dmc_unrar-1.8.0-hmdfs-inode-enospc-sparse-checkout：HMDFS inode 池耗尽导致 git worktree 全量检出报 "No space left on device"（磁盘未满），用 sparse-checkout cone 规避

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-21
> Source: dmc_unrar 1.8.0 适配（build_in_harmonyos 大仓 worktree 创建）
> 对应：`knowledge/drafts/DRAFT-dmc_unrar-1.8.0-hmdfs-inode-enospc-sparse-checkout.kv`

## 现象

`git worktree add` 创建新库专用 worktree 时失败，报磁盘空间类错误，但磁盘明明没满：

```console
error: unable to create file archives/w/wren/0.4.0/conandata.yml
fatal: cannot create directory at 'archives/w/wren/0.4.0/test_package'
fatal: cannot create directory at 'archives/l/libarchive'
```

每次失败的路径都不同（wren → libarchive → acme.sh → cunit），看起来"随机"，重试仍失败；
`git worktree add --no-checkout` + `git reset --hard` 也卡在 `Unable to create '.../index.lock': No space left on device`。

## 诊断

```console
$ df -h /storage/Users/currentUser   # 磁盘：928G 总量，330G 可用 —— 没满
$ df -i /storage/Users/currentUser   # inode：48455677 总量，IUsed 48450677，IFree ~5000 —— 100% 耗尽！
```

**根因**：/storage 挂载在 HMDFS 分布式文件系统上，inode 总数固定（约 48.45M）且被本机
**所有执行端共享**。仓库越大，单次全量 checkout 消耗的 inode 越多
（build_in_harmonyos 有 77,768 个文件 → 需要 7.7 万个 inode）。
并发执行端创建其他库 worktree 抢占 inode 后，剩余 inode 不足以完成全量检出，
写任何新文件都返回 ENOSPC —— 表现成"磁盘满"，实为"inode 满"。

`git worktree add` 在 checkout 中途失败会回滚整个 worktree，因此每次都从零开始，
在 inode 接近临界时表现成"随机路径失败"。

## 修复（已验证）

1. **确认**：`df -i` 看 inode 使用率（而非只看 `df -h`）。
2. **释放**：清理自己残留的未完成 worktree/partial 目录（`git worktree prune`、删除 partial `.orig/.work`），恢复 inode 余量。
3. **稀疏检出**：先 `git worktree add --no-checkout <path> <branch>`（不填充文件），再：

```bash
git sparse-checkout set --cone scripts ci knowledge templates references config docs probes code tests .gitcode archives/d
git reset --hard HEAD
```

只映射任务实际需要的顶层目录（配方、脚本、CI、知识图谱、当前库的字母分片），
文件数从 77,768 降到 6,663，一次成功。

4. **收敛重试**：若 reset 中途仍偶发 ENOSPC，循环重跑 `git reset --hard HEAD`
   （已落盘文件被跳过），几次内收敛；注意中断的 reset 会留下 `index.lock`
   （0 字节，无 index 文件），需先删除锁再重试。

## 后续注意

- 稀疏检出下 `git ls-files` 仍含全部 77,768 个条目（index 完整），仅工作树不落盘。
- 其他库提交前已有的 `.build-closed`/`.staging-verified` 等隐藏基线文件仍会被
  `jc` 类全量门禁扫到，按基线隔离规程（记录 SHA-256 → 临时隔离 → 复跑 → 原样恢复）处理。
- 本条目与 E497（git 元数据放 HMDFS 的另外一类问题）同域但不同因。

## 适用边界

- 仅适用于 inode 池为硬上限且多执行端共享的文件系统（HMDFS /storage）。
- ext4/tmpfs（inode 充足）不适用；工具链需能容忍未映射目录不可见。
