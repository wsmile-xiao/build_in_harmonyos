# DRAFT: HMFS 对 FS_IOC_MEASURE_VERITY 返回 EACCES — composefs 1.0.8 适配实证

## 问题
composefs 1.0.8 在 HarmonyOS PC（HMFS 用户数据分区）上运行 `mkcomposefs` 构建镜像时，
对目录树扫描报 `error accessing <path>: Invalid argument` 并中止；`test-lcfs` 的
`lcfs_fd_measure_fsverity` 断言路径同样异常。探针定位到：
对普通文件执行 `ioctl(FS_IOC_MEASURE_VERITY)`，HMFS 返回 **errno=13 (EACCES)**，
而 Linux（ext4/overlayfs）对未启用 fs-verity 的文件返回 **ENODATA**、对不支持该 ioctl
的文件系统返回 **ENOTTY/EOPNOTSUPP**。

## 根因
composefs `lcfs_fd_measure_fsverity`（lcfs-writer.c:581）只把
`ENODATA/EOPNOTSUPP/ENOTTY` 归一化为 `ENOVERITY`；HMFS 用 EACCES 表达"本文件系统
不支持 fs-verity"，落入该函数与 `lcfs_fd_get_fsverity` 的"意外错误"分支（不回退），
使 `lcfs_build` 对整个目录扫描失败。这是 HarmonyOS 文件系统 ABI 与 Linux 的 errno 语义偏差，
不是文件权限问题（chmod 无法消除）。

## 方案
最小补丁（libcomposefs/lcfs-writer.c）：把 `FS_IOC_MEASURE_VERITY` 的 **EACCES**
（以及 EINVAL 变体）与 ENODATA/EOPNOTSUPP/ENOTTY 一并归一化为 ENOVERITY，调用方即走
"内核无 fs-verity"分支，回退到 composefs 已有的**进程内 fs-verity 摘要计算**
（lcfs_fd_get_fsverity 的 lseek+compute 路径）。

## 验证（本轮真实日志）
- ioctl 探针（C 程序）：HMFS 上 `ioctl(FS_IOC_MEASURE_VERITY)` r=-1 **errno=13 EACCES**（文件与目录一致）
- 补丁后：`lcfs_fd_measure_fsverity` 返回 **-25 (-ENOVERITY)**（ohos_fsverity_test 断言 PASS）
- `lcfs_fd_get_fsverity` 返回 0，摘要确定（同内容同摘要、异内容异摘要，两处断言 PASS）
- `check-units`（mkcomposefs 目录扫描）test_inline/test_objects/test_mount_digest 全 PASS

## 适用边界
- 适用：任何在 OHOS HMFS 上探测 fs-verity 能力的库/工具（composefs mkcomposefs、lcfs_build）
- 不适用：真实 Linux ext4（EACCES 确有"无权限测量"语义，不可盲目归一化；本方案只面向
  OHOS HMFS 平台，patch guard=hmfs）

## 查重差异（七轴摘要）
| 轴 | 结论 |
|---|---|
| exact_duplicate | 否（知识库无 fs-verity ioctl EACCES 条目，fsverity 关键词 0 命中） |
| causal_duplicate | 与 DRAFT-tar-1.35-hmdfs-dir-xattr-einval 同属 HMFS ABI 偏差族，但根因函数不同（ioctl vs getxattr） |
| trigger_overlap | 无（ioctl errno 语义） |
| solution_overlap | 无（errno 归一化方案为新增） |
| combination_novelty | 是（errno 归一化 + 进程内摘要回退组合） |
| boundary_novelty | 是（EACCES∈"无 fs-verity"集合的边界） |
| test_migration_novelty | 是（ohos_fsverity_test 专项断言迁移） |

关系：similar_to=DRAFT-tar-1.35-hmdfs-dir-xattr-einval；无 prerequisite/conflicts。
