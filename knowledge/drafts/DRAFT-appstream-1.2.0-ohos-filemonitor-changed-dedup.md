# DRAFT-appstream-1.2.0-ohos-filemonitor-changed-dedup — GFileMonitor 事件顺序差异（ATTRIBUTE_CHANGED 先于 CREATED）→ 同批 added 去重

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: build / glib / gio / filesystem
> **Audience**: 使用 GLib GFileMonitor 消费事件、按 attached/dedupe 语义聚合的库与测试

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R03）：as-test_pool test_filemonitor_dir
  在 touch 新文件后断言 `cnt_changed == 0`，实测得到 1。

## 症状（symptom）

```
# DEBUG: modified: <dir>/test.txt ATTRIBUTE_CHANGED [0]   ← 先于 CREATED 到达
# DEBUG: Emit ::added(<dir>/test.txt)
ERROR: ../tests/test-pool.c:...: assertion failed (cnt_changed == 0): (1 == 0)
```

同一新文件既发 added 又发 changed；纯 Qt/多文件系统平台上事件投递顺序与桌面 Linux 不同。

## 机制（root cause）

as_file_monitor_process_pending 先发 queue_changed 再发 queue_add；OHOS 文件系统
事件序中 ATTRIBUTE_CHANGED/CHANGED 可能先于 CREATED 到达，导致文件尚在
queue_add/queue_temp 中就被排队为 changed。上游假设 CREATED 先到（Linux 语义）。

## 修复（fix）

0005-filemonitor-changed-dedup.patch：process_pending 发 changed 前检查该路径是否
同时在 queue_add（将作为 added 发出）或 queue_temp（原子保存临时文件，稍后经
RENAMED 转 added）——命中则跳过 changed，避免重复事件。

## 验证（verification）

- as-test_pool 10/10 PASS（rc=0），test_filemonitor_dir 断言全过。

## 适用边界 / 反例

- 适用：任何消费 GFileMonitor 事件并在文件系统事件序不稳的平台上做 added/changed
  聚合的实现；
- 反例：平台事件序稳定（CREATED 恒先于 ATTRIBUTE）时改动无行为差异，可不上。

## 关系

- 查重：grep "file_monitor|inotify|G_FILE_MONITOR" 在 knowledge/graph/ 无命中。
- similar_to: []；caused_by: []；prerequisite_of: []；conflicts_with: []

## 证据

- 补丁：archives/a/appstream/1.2.0/patches/0005-filemonitor-changed-dedup.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 8
