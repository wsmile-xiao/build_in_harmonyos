# DRAFT-appstream-1.2.0-r05-ohos-otmpfile-linkat-probe — O_TMPFILE 打开成功但 linkat(/proc/self/fd) 发布被禁 → 探测回退命名文件+renameat

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: medium (2) | **Category**: filesystem / O_TMPFILE / linkat / /proc
> **Audience**: 用 O_TMPFILE 写临时产物、再经 /proc/self/fd linkat 发布的服务

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R05）：asc_media_out_slot_commit
  渲染 orig.png 时 `Unable to store the rendition 'orig.png': Permission denied`。

## 症状（symptom）

```
linkat (AT_FDCWD, "/proc/self/fd/N", dir_fd, name, AT_SYMLINK_FOLLOW) → EACCES (13)
```

## 机制（root cause）

OHOS 挂载 /proc，但 seccomp/权限层面拒绝经 `/proc/self/fd/N` 以
`linkat(AT_SYMLINK_FOLLOW)` 发布 O_TMPFILE 匿名 inode（EACCES）。O_TMPFILE
打开本身可用；命名临时文件 + renameat 实测正常。

## 修复（fix）

0014-asc-media.patch：`asc_media_use_tmpfile()` 探针在受信目录实测
O_TMPFILE 打开 + linkat(/proc/self/fd) 发布；失败即回退"命名隐藏临时文件
（`.asc-tmp-xxxx`）→ renameat 原子改名"，保留崩溃不残留临时产物的语义尽量接近。

## 验证（verification）

- as-test_compose MediaImage：orig.png/64.png 落盘、4000.png 仅降级跳过全部断言通过；
  日志可见 `O_TMPFILE can not be published via /proc on this platform, using named temporary media files.`

## 适用边界 / 反例

- 适用：需要无残留临时产物、但又受 /proc 发布限制的平台；
- 反例：/proc 可正常 linkat 的平台（探针直接放行 O_TMPFILE，性能更好）。

## 关系

- 查重：DRAFT-ohos-otmpfile-tmpdir-shim（EACCES→LD_PRELOAD 重定向 /tmp 只读场景）
  局限"打开"阶段；本候选是"打开成功、发布被禁"，方案为库内回退 renameat。
- similar_to: DRAFT-ohos-otmpfile-tmpdir-shim；caused_by: []; prerequisite_of: []; conflicts_with: []

## 证据

- 补丁：patches/0014-asc-media-tmpfile-linkat-probe.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 17