# DRAFT-ledmon-0.97（成套实例·通用机制 M10）: /dev/shm 只开放"数据面"——**连自家 shm_open 文件上的 flock 都被拒(EACCES)**，ledmon 实证且上游不查返回值 ⇒ 静默互斥失效

> 蓝本：`经验文档/B草稿库/DRAFT-PKG-VER-dev-shm-write-only-virtual-dir.{kv,md}`（DS-20，2026-09-21，
> §12.77 M10）。本文件是 **ledmon 0.97 的包侧成套实例**：证据换成本包真机实测，并补两条蓝本未覆盖的增量
> （见"新增价值"节）。

## 基本信息
- **严重度**: 2
- **类别**: platform, hmdfs, posix, tmpdir
- **作者**: hw-5
- **来源 PR**: #12454（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12454）
- **来源 commit**: 0be185fd2997bad956442f33ab7463914af6dabb

## 错误特征
```
shm_open("/ledmon_amd_sgpio_cache", O_RDWR|O_CREAT)  → OK（数据面）
flock(cache_fd, LOCK_EX|LOCK_NB)                     → r=-1 errno=13 (Permission denied)
flock(cache_fd, LOCK_SH|LOCK_NB)                     → r=-1 errno=13 (Permission denied)
```
**关键判据（本条的灵魂）**：**同一个 /dev/shm 文件，创建/读写/mmap/fsync 全部成功，唯独锁被拒**——
"只用 /dev/shm 下的文件、不碰目录"**不等于**不受 M10 影响；锁属于控制面。

## ledmon 真机实测（2026-09-24，OHOS aarch64 / clang 15，uid=20020084，探针逐字复现上游调用序列）

| 操作（复现自 ledmon 源码位置） | 结果 | errno |
|---|---|---|
| `shm_open("/ledmon_amd_sgpio_cache", O_RDWR\|O_CREAT)` + `ftruncate` + `mmap` 写读（amd_sgpio.c:229-241） | ✅ OK | — |
| **`flock(fd, LOCK_EX\|LOCK_NB)` 于该 shm fd**（同上） | ❌ FAILED | **13 EACCES** |
| **`flock(fd, LOCK_SH\|LOCK_NB)`** | ❌ FAILED | **13 EACCES** |
| `fsync` + `close` + `shm_unlink` | ✅ OK | — |
| `snprintf("/dev/shm%s")` 拼路径 + `open/read/unlink` "/dev/shm/ledmon.conf"（ledctl.c:895-905 / config_file.c:283） | ✅ OK 全链路 | — |
| 蓝本矩阵（DS-20, 2026-09-21）：`opendir`/`mkdir`/`fcntl(F_SETLK)`/`futimens`/`utimensat`/`inotify_add_watch` 于 /dev/shm | ❌ FAILED | 13 EACCES |
| 对照：HMDFS($HOME) 普通文件 `flock`/`fcntl(F_SETLK)`/OFD 锁 | ✅ 正常且跨进程生效 | — |

原始输出留档：设备 `~/tmp/uc2/hw-5/probe/{probe_ledmon_shm.c,out.log}`（EXIT=0，逐字含上面三行）。

## 一句话模型
**`/dev/shm` 只开放"数据面"**（按名寻址 + 读写 + mmap + 删除），**关闭"元数据/控制面"**
（枚举、建目录、**文件锁**、时间戳、inotify）——**锁加在自己 shm_open 出来的文件上也不例外**；
所有被拒操作 errno 一律 EACCES(13)。

## 根因分析
**推断（未取证内核/namefs 实现）**：OHOS `/dev/shm` 由 namefs 管理，呈现"只写虚拟目录"语义；
锁请求需要底层 inode 语义支持，namefs 直接拒绝。**实测事实仅限上表 errno**，勿据此断言实现细节。

## 新增价值（相对蓝本 M10 / E303）
1. **封堵 safety_boundary 的误读面**：蓝本写"只用 /dev/shm 下文件的实现不受本条影响"——ledmon 证明
   "只用文件 + 在文件上加 flock"的实现**照样踩**；适用性判定必须落到**操作粒度**，不是"文件/目录"二分。
2. **静默失效形态**：上游 `_open_and_map_cache()` **不检查 flock 返回值**——失败无报错、无降级，
   进程照跑，只是并发 ledmond/ledctl 对缓存区的写保护**静默消失**。这是"控制面被拒"最危险的消费形态：
   没有错误签名可 grep，只能靠探针建立"应有锁而锁必失败"的基线。
3. 附带一条**证伪记录**：`/var/tmp` 在整机不存在（mkdir errno=2 ENOENT），
   `smp.c:280` 的 mknod 路径根本到不了 CAP_MKNOD 判定——排查同族"造设备节点"包时先测目录存在性。

## 推荐方案
**方法**: `route-shm-locks-and-dir-ops-off-dev-shm`

- 目录类操作（mkdir/opendir/mkdtemp）改道 TMPDIR/XDG_RUNTIME_DIR（蓝本原方案）；
- **锁类操作**：先回查上游是否检查返回值。可容忍协作型锁 → 显式检查 + warning 留痕（禁止静默吞）；
  正确性必需锁 → 换锁载体（锁文件放可写目录，或命名 `sem_open`——实测可用）；
- ledmon 本包处置：数据面无需改动即工作；锁失效面在 notes.md 申报为运行期已知限制
  （root daemon 无并发写者场景影响可控），不改上游语义。

**验证**: `clang -O1 --target=aarch64-unknown-linux-ohos --sysroot=$HOME/usr/local/sysroot -o probe probe_ledmon_shm.c && ./probe`

## 适用边界 / 反例 / 解除条件
- **适用**：在 /dev/shm 上做控制面操作（目录/枚举/**flock/fcntl 锁**/时间戳/inotify）的包；
- **不适用**：纯数据面用法（open/write/mmap/unlink/shm_open/sem_open 且不依赖锁）——实测全部可用；
- **反例/风险**：把 flock 失败当"环境不支持"整体降级 ⇒ 连带跳过真实功能路径；修的是操作载体，不是测试强度；
- **解除条件**：OHOS 提供 /dev/shm 上可用的文件锁语义（当前无时间表）。

## 关键词
/dev/shm, namefs, 只写虚拟目录, EACCES, flock, fcntl F_SETLK, shm_open, 静默互斥失效, ledmon, amd_sgpio,
mkdir, opendir, mkdtemp, utimensat, futimens, inotify, POSIX 共享内存, 命名信号量

---
*与相近条目的区分：**E303** 只覆盖"目录枚举被拒"半区（蓝本 draft-review score=0.48 灰区）；
**DRAFT-E577** 讲 SysV IPC→POSIX 迁移，本条继续作为其推荐解法的可用性实证；
**E022/E110/E002** 同族但被禁操作不同。蓝本 `DRAFT-PKG-VER-dev-shm-write-only-virtual-dir` 与本实例互指，
按 §12.77 M10 成套配送。*
