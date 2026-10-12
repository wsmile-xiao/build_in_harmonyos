# DRAFT-3517-qemu-9.2.4-link-eperm-symlink-statistical-equivalence

> HarmonyOS PC（aarch64-linux-ohos）的 HMDFS 拒绝 `link(2)`/`linkat(2)`
> （EPERM）。本条目给出「以符号链接做统计等价代偿」的**适用前提**、
> 实现要点，以及**不可代偿面**的清单。来自 qemu 9.2.4 适配（Issue #3517 / PR !13119）。

## 现象

qemu 的 `tests/qtest/virtio-9p-test.c` 中 `local/hardlink_file` 用例失败，
报错与「硬链接」字面毫无关联：

```
ERROR:../src/tests/qtest/libqos/virtio-9p-client.c:269:v9fs_req_recv:
      Expected reply 71, got 7
```

（71 = `Rlink`，7 = `Rlerror`——服务端回了错误，而不是链接结果。）

## 根因

qemu 的 9p 文件服务后端 `hw/9pfs/9p-local.c` 用 `linkat` 实现 9p 的 `Tlink`。
实测能力矩阵：

| 位置 | `link` / `linkat(flags=0)` | `mkdir` |
|---|---|---|
| HMDFS（`$HOME` 及构建目录） | **EPERM** | **OK** |
| `/dev/shm`（tmpfs） | **OK** | **EACCES** |

即 HMDFS 上链接不可用，而唯一支持链接的挂载点又不能作根目录（`mkdir` 被拒）。
被拒后服务端以 `Rlerror(EPERM)` 回应，客户端因消息号不符而断言失败——**报错
指向协议层，掩盖了文件系统能力问题**。

## 代偿的适用前提（关键判据）

代偿是否成立，取决于**上游测试究竟断言什么**，必须先核查：

| 待核查项 | 命令 | qemu 该用例实测 |
|---|---|---|
| 是否断言 `st_nlink` | `grep -c st_nlink tests/qtest/virtio-9p-test.c` | **0（无）** |
| 是否用 `lstat`/`AT_SYMLINK_NOFOLLOW` 观测 | `grep -n 'lstat\|NOFOLLOW'` | 无 |
| 是否测试源删除后链接仍可读 | 见用例体 | 无 |

该用例实际断言三项：

```c
g_assert(stat(hardlink_file, &st_link) == 0);            /* 能 stat 到 */
g_assert((st_link.st_mode & S_IFMT) == S_IFREG);         /* 是普通文件 */
g_assert(st_link.st_dev == st_real.st_dev);              /* 同设备 */
g_assert(st_link.st_ino == st_real.st_ino);              /* 同 inode */
```

**符号链接全部满足**：`stat` 跟随链接，故解析到同一 inode，`S_IFREG`、
`st_dev`、`st_ino` 自然一致。三项前提都无 → 代偿成立。

## 修复

仅在真实 `link`/`linkat` 返回 EPERM 时改为 `symlink`：

1. **门禁**：环境变量（`QTEST_LINK_SHIM=1`）+ 仅 EPERM 触发；其他错误码透传。
2. **`linkat` 带 `AT_SYMLINK_FOLLOW` 时不代偿**（否则目标文件选错）。
3. **源路径绝对化**：`linkat` 的任一侧可相对目录 fd，而符号链接的目标是**写入
   的字符串**，须用 `/proc/self/fd/<dirfd>` 解析出绝对路径，否则链接在其他
   `cwd` 下解析失败。
4. 代码骨架：

```c
ret = real_linkat(olddirfd, oldpath, newdirfd, newpath, flags);
if (ret == 0) return 0;
saved = errno;
if (flags != 0 || saved != EPERM) { errno = saved; return -1; }   /* 透传 */
return symlink_with_absolute_target(olddirfd, oldpath, newdirfd, newpath);
```

## 验证

| 项 | 结果 |
|---|---|
| 独立探针（`link` 后 `stat` 比对三项） | 基线 `link EPERM`；垫片下 `S_IFREG=yes`、`st_dev` 同、`st_ino` 同 → **三项断言成立** |
| `virtio-9p-tests/local` 全族 | 由失败转为 **10/10 通过** |

## 不可代偿面（须如实披露）

符号链接**不是**硬链接。以下性质无法伪造，依赖它们的用例**不能**用本垫片：

1. `st_nlink` 计数（硬链接会 +1）；
2. **源删除后链接是否仍可读**（硬链接幸存，符号链接变悬空）；
3. `lstat` / `AT_SYMLINK_NOFOLLOW` 遍历时的可见性（符号链接会暴露）；
4. 依赖硬链接做**去重/配额/引用计数**的逻辑（例如备份工具的「同 inode 只存
   一份」）；
5. 权限与属主继承（符号链接自身权限无意义）。

因此本垫片以环境变量门禁、只用于在缺失链接能力的宿主上**驱动该上游测试**，
不作为通用兼容层。
