# DRAFT: posix_fallocate 在 HMDFS 的返回码语义陷阱

## 场景

上游代码（libaudit 2.7.4 `audisp/plugins/remote/queue.c` 的
`q_open_file()`）用 posix_fallocate 预分配队列文件：

```c
#ifdef HAVE_POSIX_FALLOCATE
        if (posix_fallocate(q->fd, 0,
                            (q->num_entries + 1) * q->entry_size) != 0)
                return -1;
#endif
```

测试 `test-queue` 在 OHOS 上报
`test-queue: 264: q_open: Result not representable`（errno=34 ERANGE）。

## 症状与根因

实测（OHOS 设备，HMDFS 家目录）：

```
posix_fallocate rc=13 errno=999 (errno 未被触碰)
```

- **HMDFS 不实现文件预分配**：posix_fallocate 返回 EACCES(13)；
- **errno 未被设置**：这是 POSIX 允许的——posix_fallocate 失败时
  **返回错误编号本身**，errno 无保证（glibc 恰好双设，掩盖差异）；
- 上游 `!= 0` 即失败的判断没问题，但**移植者的第一反应**往往是加
  errno 白名单降级（`errno != EOPNOTSUPP` 之类）——此时读到的是
  调用链残留 errno（本例为 strtoul 留下的 ERANGE=34），把“文件
  系统不支持”误判成真失败，`strerror(34)` 恰好输出
  "Result not representable"，极具误导性。

## 修复

用**返回码**做白名单判断（POSIX 语义），不支持类错误降级
ftruncate（文件大小保证等价）：

```c
int fa_rc = posix_fallocate(q->fd, 0, size);
if (fa_rc != 0 && fa_rc != EINVAL && fa_rc != ENOSYS
    && fa_rc != EOPNOTSUPP && fa_rc != EACCES && fa_rc != EPERM) {
    errno = fa_rc;      /* 真失败才透传 */
    return -1;
}
if (ftruncate(q->fd, size) != 0)   /* 预分配只是优化，truncate 兜底 */
    return -1;
```

## 验证

- 修复前：test-queue abort 于 q_open（ERANGE 残留）；
- 修复后：test-queue 四组 flags（IN_MEMORY/IN_FILE/IN_FILE|SYNC/
  BOTH）+ test_resizing 全部通过（上游 make check PASS）。

## 适用面

任何在 HMDFS 上调用 posix_fallocate 的移植（队列/缓存/数据库
预分配场景常见）。判定特征：`strerror(errno)` 报一个与文件系统
毫无关系的错误（ERANGE/EINVAL 等）而实际返回码是 EACCES。
