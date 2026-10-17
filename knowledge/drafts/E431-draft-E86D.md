# E431 — OHOS HMDFS 不支持 mknod/FIFO：上游 FIFO 类测试为平台阻塞

## 错误特征
- `mknod(fifo_path, S_IFIFO|0666, 0)` 返回 -1，errno=EPERM（Operation not permitted）
- Python: `PermissionError: [Errno 1] Operation not permitted`（os.mkfifo）
- 典型日志：`Could not create FIFO at: ninja_test_jobserver_fifo-<rand>/fifo`

## 触发条件
- 测试/工具：ninja Jobserver.PosixFifoClient、make jobserver、任何 mknod/FIFO IPC 进程池
- 阶段：runtime（测试初始化）
- 平台：HarmonyOS PC（OHOS aarch64），当前执行用户为非 root（uid 20020101）

## 根因分析
OHOS 设备上当前用户可写的挂载点全部为 HMDFS（hmdfs 不保留 FIFO inode 语义，
mknod 返回 EPERM）；`/dev/shm` 等 tmpfs 挂载点被权限拒绝（EACCES）；
`/tmp` 为只读 erofs（Read-only file system）；其余候选（/storage/hmdfs、
/data/local/tmp、/mnt/hmdfs/100/non_account、/sys/fs/cgroup 等）均 EPERM/EACCES。
全候选挂载点验证后，设备上不存在任何"可写且支持 POSIX FIFO 且保留真实 0700"的挂载点
（HMDFS 目录 chmod 700 后 stat 仍 0o2771，chmod 被忽略）。

## 解决方案

### 推荐方案
如实记录为平台阻塞并给出恢复条件（document-platform-block）：
```bash
# 逐项验证候选挂载点（R01/R02/R03 三轮回放均失败）：
toybox mkfifo /storage/Users/currentUser/tmp/f   # EPERM Operation not permitted
toybox mkfifo /dev/shm/f                          # EACCES
toybox mkfifo /tmp/f                              # Read-only file system
```
恢复条件：提供支持 mknod/FIFO 且保留真实 0700 语义的可写挂载点（ext4/tmpfs 且 hmmac 放行）。

### 禁止做法
- ❌ 把 FIFO 用例伪写为通过/跳过/未运行
- ❌ 修改上游测试绕过 FIFO 断言
- ❌ 用 env-var-override 单线程绕过（E074 方案对本轮无解，仍记录阻塞）

## 验证
```bash
python3 -c "import os;os.mkfifo('/storage/Users/currentUser/tmp/x')"  # → EPERM
# 全候选挂载点逐一验证记录见台账 3.1 与 ledger 五、四节
```

## 适用边界
- 适用：依赖 FIFO/mknod 的构建工具与测试（ninja/make jobserver、IPC 进程池），OHOS 设备
- 反例：提供 ext4/tmpfs 可写挂载点后 FIFO 可建，用例可恢复运行

## 查重差异
- exact_duplicate: false；causal_duplicate: false（E074 根因写 SELinux 策略；本轮实测为 HMDFS mknod 语义 + 全候选挂载点）
- trigger_overlap: true（E074/E292 的 jobserver FIFO 正则可命中本错误）
- combination_novelty: true —— 全候选挂载点验证流程与"设备上不存在任何可写且支持 POSIX FIFO 的挂载点"结论

## 关联条目
- similar_to: E074、E292
- caused_by: HMDFS 文件系统 mknod 语义 + 平台挂载限制
- conflicts_with: 无
