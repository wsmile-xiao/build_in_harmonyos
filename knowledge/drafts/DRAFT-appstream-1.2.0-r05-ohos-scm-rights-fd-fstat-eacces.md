# DRAFT-appstream-1.2.0-r05-ohos-scm-rights-fd-fstat-eacces — OHOS 拒绝跨进程 SCM_RIGHTS fd 的 fstat → fcntl/lseek/mmap 替代

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: medium (2) | **Category**: ipc / fd / SCM_RIGHTS / fstat / EACCES
> **Audience**: 通过 Unix socket SCM_RIGHTS 传 fd 给子进程处理，并在接收侧用 fstat 校验/取尺寸的服务

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R05）：compose mediaworker 处理图片/字体
  - `Unable to stat received fd: Permission denied`（asw_memfd_verify_sealed 内 fstat errno=13）
  - GLib `g_mapped_file_new_from_fd` 内部 fstat 失败：
    `Failed to get attributes of file 'fd': fstat() failed: Permission denied`

## 症状（symptom）

```
ERROR: test-compose.c: MediaImage: assertion failed (error == NULL):
  Unable to stat received fd: Permission denied
```

## 机制（root cause）

OHOS（HMDFS/安全策略）对通过 `SCM_RIGHTS` 跨进程传递的 fd 拒绝 `fstat()`（EACCES 13），
但同一 fd 的 `fcntl(F_GETFL)`、`fcntl(F_GET_SEALS)`、`lseek()`、`mmap()` 均被允许。
最小 C 复现（socketpair + SCM_RIGHTS + fstat）双向验证：子进程 fstat → EACCES，
F_GETFL/lseek/mmap 正常。上游所有"fstat 校验 S_ISREG + 取 st_size"的路径全断。

## 修复（fix）

- 0012-asw-ipc.c：`asw_memfd_verify_sealed` —— fstat EACCES 视为平台情形放行，
  安全门改为 `fcntl(F_GET_SEALS)`（F_SEAL_SHRINK|GROW|WRITE），尺寸用
  `lseek(fd, 0, SEEK_END)` 推导。
- 0013-asw-worker.c：`asw_worker_get_readonly_file_fd` / `asw_worker_get_output_fd`
  —— fstat EACCES 放行，改用 `fcntl(F_GETFL)` 的 O_ACCMODE 校验读写权限。
- 0015-asw-font.c：`asw_font_new_from_fd` —— 弃 `g_mapped_file_new_from_fd`
  （内部 fstat），改 lseek 取尺寸 + mmap(PROT_READ, MAP_PRIVATE) 直映，
  由 GBytes free func munmap 释放。

## 验证（verification）

- as-test_compose 18/18（含 MediaImage / MediaFont）、as-test_compose-worker 10/12
  + 2 能力跳过；上游 14/14。
- 最小 C 复现：fstat EACCES 且 fcntl/lseek/mmap 可用。

## 适用边界 / 反例

- 适用：SCM_RIGHTS 跨进程传 fd 的服务（media worker、sandbox IPC 等）；
- 反例：同进程自开 fd 的 fstat 正常，无需改；仅缺库场景（如只读校验必须 stat）另议。

## 关系

- 查重：E008（fstat EACCES）覆盖**同进程管道/终端**——触发面是 fd 类型而非跨进程传递，
  方案是"回退安全默认值"；本候选方案为换 API 面（fcntl/lseek/mmap）。
- similar_to: E008；caused_by: []; prerequisite_of: []; conflicts_with: []

## 证据

- 补丁：patches/0012-asw-ipc-fd-stat-ohos.patch、0013-asw-worker-fd-stat-ohos.patch、
  0015-asw-font-fd-map-ohos.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 15
