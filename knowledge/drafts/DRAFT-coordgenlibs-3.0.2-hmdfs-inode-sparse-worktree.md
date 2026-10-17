# HMDFS inode 耗尽表现为 ENOSPC：git worktree 检出与依赖源码解压失败

> Draft（未 promote）— 来源于 coordgenlibs 3.0.2 适配（task coordgenlibs-3.0.2-r01-pc1-45, 2026-09-25）
> 对应 `.kv` 文件同 stem：`DRAFT-coordgenlibs-3.0.2-hmdfs-inode-sparse-worktree.kv`

## 问题

在 HMDFS 账户文件系统上执行 `git worktree add` 全量检出大型 monorepo、或
`conan create` 解压大依赖源码（如 boost）时，报错：

```
fatal: cannot create directory at 'archives/c/<...>/test_package'
error: unable to create file archives/c/<...>/test_package/CMakeLists.txt
OSError: [Errno 28] No space left on device
```

失败点在多次重试中漂移（cpuinfo → cpplocate → cmp → coin），重复重试无效。

## 根因

- `df -h` 显示仍剩数百 GB（如 928G 总、360G 可用）——**容量充足**；
- 但 `df -i` 显示 **inode 使用率 100%**（如 48450677/48455677），仅剩数千；
- 全量检出需要一次性创建 88.7k+ 文件（本仓 main），boost 源码解压 ~150k 文件，
  远超过剩余 inode，于是以 ENOSPC 失败 —— **真正瓶颈是 inode 配额，不是容量**。

## 方案

1. **判别**：`df -i <账户根> | tail -1` 看 IUse% 与 IFree；同时 `df -h` 对比容量。
2. **worktree 创建**（sparse，git 元数据完整）：
   ```bash
   git worktree add --no-checkout <path> <branch>
   git -C <path> sparse-checkout init --cone
   git -C <path> sparse-checkout set scripts references templates ci .gitcode knowledge archives/<首字母>/<库名>
   git -C <path> checkout
   ```
   文件数从 88.7k 降到 ~4.7k；分支/HEAD/commit/push/diff/PR 审计不受影响。
3. **conan 依赖源码解压失败**：
   ```bash
   conan cache clean "*"                 # 清理损坏/残留包
   rm -rf ~/.conan2/p/<残缺包>           # 释放被占 inode
   ```
   优先复用本地缓存中已构建的依赖二进制（头文件与库已在缓存），避免再次源码解压。
   若 registry 有匹配 profile 的预编译 binary，用 `conan install` 拉取而非 `--build=missing` 源码构建。

## 验证

- coordgenlibs 3.0.2：全量检出 3 次失败后，sparse 检出成功；
- 同一 sparse worktree 内完成 init-build → lang-preflight → conan-verify
  （G0-G4/L2/L4/L5 全 PASS）→ finish/W3 全门禁；上游测试 20/20；
- test_package 消费者测试 2/2 通过。

## 适用边界

- 适用：HMDFS 账户 inode 配额耗尽、操作需要一次性创建海量文件的场景；
- 不适用：inode 充足的文件系统；需要整仓文件在物理盘存在的操作（整仓 grep 工具）。

## 反例

- 小仓库（几百文件）在 inode 余量充足时无需 sparse 方案；
- sparse 方案不能让仓库级脚本直接 `ls archives/<letter>/<name>` 读取全部归档，
  需在 sparse set 中显式加入目标路径。