# DRAFT-3517-qemu-9.2.4-hmdfs-shm-fallocate-lock-mutual-exclusion

> HarmonyOS PC（aarch64-linux-ohos，HongMeng Kernel 1.12.0）上，
> **HMDFS 与 /dev/shm 的 fallocate 能力与文件锁能力互斥**，导致
> 「把临时文件挪到 /dev/shm」这类直觉修法会把一个问题换成另一个问题。
> 本条目来自 qemu 9.2.4 适配（Issue #3517 / PR !13119）。

## 现象

qemu 9.2.4 的 `tests/qtest/virtio-blk-test.c` 断言 virtio-blk 的
`WRITE_ZEROES` 请求返回 `status == 0`（`virtio-blk-test.c:221`）：

```
ERROR:../src/tests/qtest/virtio-blk-test.c:221:test_basic:
      assertion failed (status == 0): (1 == 0)
```

该用例的 raw 映像由 `g_file_open_tmp("qtest.XXXXXX")` 创建（即位于 TMPDIR），
随后被 QEMU 以 `-drive file=...,format=raw,auto-read-only=off` 打开。

把映像重定向到 `/dev/shm` 后，失败**变了形状**，看起来毫不相干：

```
qemu-system-arm: -drive if=pflash,file=.../qtest.5QZ4V3,format=raw:
                 Failed to lock byte 100
socket_accept failed: Resource temporarily unavailable
ERROR:../src/tests/qtest/libqtest.c:497:qtest_init_internal:
      assertion failed (s->fd >= 0 && s->qmp_fd >= 0)
```

即 QEMU 在**连接 qtest socket 之前**就退出了，表现为 50s 超时
（`SOCKET_TIMEOUT`），极易误判为 socket/垫片/环境问题。

## 根因

两类能力在两个可写挂载点上**恰好互补**（均为本机实测）：

| 挂载点 | `fallocate(PUNCH_HOLE)` | `fcntl(F_SETLK)` |
|---|---|---|
| HMDFS（`$HOME` 及构建目录） | **EACCES** | **OK** |
| `/dev/shm`（tmpfs, 1.0G） | **OK** | **EPERM**（`F_OFD_SETLK` 同） |
| `/tmp` | 只读挂载（EROFS），不可用 | — |

- QEMU 的 `block/file-posix.c` 在打开 raw 映像时对
  `RAW_LOCK_PERM_BASE` 起的字节逐个加锁（报错点即 `file-posix.c:876`
  → `"Failed to lock byte %d"`，实测为 byte 100）。`/dev/shm` 上
  `fcntl` 锁被拒 → QEMU 加锁失败 → 退出 → qtest 侧 accept 超时。
- HMDFS 上锁没问题，但 `fallocate` 的 punch-hole / zero-range 被拒
  （返回 `EACCES`，不是常见的 `EPERM`/`EOPNOTSUPP`）。

结论：**没有单一挂载点能同时满足**「需要 punch-hole」与「需要文件锁」的
写者；必须按该写者是否加锁来选择挂载点，并对缺失的那一项做代偿。

## 修复

保留文件在**锁可用**的挂载点（HMDFS），只代偿缺失的原语：

1. 判断缺失的是哪一种原语，不要只看 `fallocate` 一项能力就换挂载点——先确
   认写者是否加锁（QEMU raw 映像、数据库、日志轮转类写者通常加锁）。
2. 用**零填充**代偿 punch-hole / zero-range：二者是同一契约的两种实现，
   即「该区间读回为零」。仅当上游断言是「读回为零」时语义等价；若断言的是
   稀疏性（`st_blocks`、磁盘占用），零填充**不**等价，应改为裁剪或标注
   UNSUPPORTED。
3. 代偿只对真正的「不支持」错误码生效，真实错误必须透传，避免掩盖故障：

```c
ret = real_fallocate(fd, mode, offset, len);
if (ret == 0) return 0;
saved = errno;
if (!(mode & (FALLOC_FL_PUNCH_HOLE | FALLOC_FL_ZERO_RANGE))) { errno = saved; return -1; }
if (saved != EACCES && saved != EPERM && saved != EOPNOTSUPP && saved != ENOTSUP) {
    errno = saved; return -1;      /* EBADF/EIO/ENOSPC 等必须透传 */
}
return zero_fill(fd, mode, offset, len);   /* 遵循 KEEP_SIZE 语义 */
```

4. **易漏点**：OHOS 在本机上报的是 `EACCES`（`"Permission denied"`），
   而非 `EPERM`（`"Operation not permitted"`）。只容忍 `EPERM` 的实现会
   **静默失效**——垫片被正确加载、函数被正确进入，却直接原样抛回错误
   （本包实测踩到，`fork` 出的进程内表现为「垫片无效」的假象）。

## 验证

- 修复前：`assertion failed (status == 0): (1 == 0)`。
- 修复后：`qos-test` 的 virtio-blk 子测试通过，且**byte-100 锁在 HMDFS 上
  仍为 OK**（零填充代偿不影响加锁）。
- 判别性探针（可独立复跑）：对同一目录建文件后分别调用
  `fallocate(punch)` 与 `fcntl(F_SETLK, l_start=100)`，比对返回码。

## 适用边界

- 适用：写者要求文件锁、且测试断言为「读回为零」的场景。
- 不适用：断言稀疏性/磁盘占用的场景；或写者不加锁（此时直接用 `/dev/shm`
  的真实 punch-hole 更好）。
- 与既有条目的差异：`DRAFT-libaudit-2.7.4-hmdfs-fallocate` 记录的是
  `posix_fallocate` 的**返回码/errno 语义陷阱**；
  `DRAFT-postgresql-fallocate-eacces-filezero` 记录的是**上游应把
  EACCES/EPERM 纳入回退集合**。本条目的新增判据是：**两个挂载点的
  fallocate 能力与文件锁能力互斥**，以及由此产生的「换了挂载点但失败现象
  完全变形（byte 100 锁 → socket 超时）」这一诊断陷阱。
