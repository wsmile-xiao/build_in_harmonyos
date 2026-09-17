# DRAFT-tar-1.35-hmdfs-dir-xattr-einval

## 问题
HMDFS 目录 listxattr 暴露 `security.hmmac`/`security.selinux` 等条目，但 getxattr 对
`security.hmmac` 返回 EINVAL：`tar: dir: Warning: Cannot fgetxattr: Invalid argument`、
`getfattr: getxattr failed: Invalid argument`（9 项 xattr 上游用例全部命中）。

## 根因
- HMDFS 目录级 xattr 语义与 POSIX 不一致：listxattr 列出 security.hmmac，getxattr 返回 EINVAL
- 文件级 user.* xattr 可用（os.setxattr/getxattr 实测 OK）
- 设备可写挂载点全部为 HMFS（/data/...）或顶层 tmpfs（HMDFS 语义），无 ext4/tmpfs
  全 POSIX xattr 挂载点可迁移

## 方案
1. 在支持完整 POSIX xattr 的文件系统（ext4/tmpfs）重跑受影响入口（恢复条件）
2. 无此类挂载点时用真实命令证明（挂载点枚举 + 目录 listxattr/getxattr 实测），
   如实记录平台阻塞，不得伪造通过

## 验证
- `python3 os.listxattr(dir)` → ['security.hmmac','security.selinux']；
  `os.getxattr(dir,'security.hmmac')` → [Errno 22] Invalid argument
- `tar --xattrs -cf xattr-r02.tar sub` → `Warning: Cannot fgetxattr: Invalid argument`
- `getfattr -h -d sub` → `getxattr failed: Invalid argument`
- 挂载点枚举：可写挂载点无 ext4/ext2/f2fs（logs/40-xattr-recovery-attempt.log）

## 适用边界 / 反例
- 适用：HMDFS 执行端上依赖目录级 xattr 的测试/程序
- 反例：文件级 user.* xattr 正常；ext4/tmpfs 上无此问题

## 查重差异
- 四范围 0 命中；E046/E047 为 HMDFS chmod/权限位（弱相关不同主题）
- 七轴：exact/causal/trigger/solution 均否，combination/boundary/test_migration 均新增

## 关系
similar_to=E046,E047（HMDFS 平台语义差异族，主题不同） / caused_by=HMDFS xattr 实现 /
prerequisite_of=(无) / conflicts_with=(无)

来源：tar 1.35 R02（task tar-1.35-r02-pc3-13-20260913T113300Z, pc3-13）
