# DRAFT-tar-1.35-ohos-uid-range-ustar

## 问题
OHOS/HMDFS 执行端用户 uid 空间（euid=20020101、文件属主 uid=20001006）超出 ustar/v7 头字段
21-bit octal 容量（2097151=2^21-1）。GNU tar 上游对超出字段容量的 uid 在 v7/ustar 格式下拒绝写入：
`tar: value 20001006 out of uid_t range 0..2097151`（exit 2）。默认/gnu/posix 格式用 base-256/
xheader 正常存储（exit 0），仅强制 `-H v7`/`TEST_TAR_FORMAT=v7|ustar` 的上游用例失败。

## 根因
- ustar/v7 头 uid/gid 字段为 8 字节 octal，有效容量 2097151（2^21-1）
- OHOS HMDFS 用户/文件属主 uid 映射到 2000xxxx 段，超出该容量
- 上游 GNU tar 对 v7/ustar 超出容量 uid 拒绝写入（格式规范正确行为，非适配缺陷）

## 方案
1. 以 uid<=2097151 的低 uid 用户上下文重跑受影响 v7/ustar 用例（恢复条件）
2. 低 uid 不可用时给出真实切换证据（os.setuid EPERM、su/setpriv/runuser/fakeroot 缺失、
   sudo 无 tty exit 1、低 uid 用户 shell=/bin/false），如实记录平台/权限阻塞
3. 默认格式（gnu/posix）大 uid 归档不受影响——用鸿蒙专项测试证明 base-256 往返

## 验证
- `tar cf a.tar f.txt`（默认格式）exit 0；`--format=gnu/posix` exit 0
- `--format=v7|ustar` exit 2（uid 20001006 超字段容量）
- 82 项 UIDRANGE 上游用例逐项实测失败原因一致（logs/39-uidrange-recovery-attempt.log）

## 适用边界 / 反例
- 适用：HMDFS 高 uid 映射执行端 + 强制 v7/ustar 归档的测试/工具
- 反例：普通 POSIX 执行端（uid<2097151）不触发；gnu/posix 格式不触发

## 查重差异
- 正式/图谱/草稿四范围 0 命中（仅 E086 ucred 弱相关，不同主题）
- 七轴：exact/causal/trigger/solution 均否，combination/boundary/test_migration 均新增

## 关系
similar_to=(无) / caused_by=OHOS HMDFS 用户 uid 空间映射 / prerequisite_of=(无) / conflicts_with=(无)

来源：tar 1.35 R02（task tar-1.35-r02-pc3-13-20260913T113300Z, pc3-13）
