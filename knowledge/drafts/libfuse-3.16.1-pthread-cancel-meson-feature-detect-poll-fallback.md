# Draft: libfuse 3.16.1 on OHOS — 用 meson 特性探测 + 有界 poll 替换 libc 缺失的 pthread_cancel

> Draft: `DRAFT-LIBFUSE-3161-PTHREAD-CANCEL-MESON-FEATURE-DETECT-POLL`
> Stem: `libfuse-3.16.1-pthread-cancel-meson-feature-detect-poll-fallback` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-LIBFUSE-3161-PTHREAD-CANCEL-MESON-FEATURE-DETECT-POLL
- **严重度**: 2
- **类别**: compat|libc|musl|threading|meson|ohos-platform
- **触发工具**: conan|clang|meson|ninja|ld.lld
- **阶段**: linking|runtime
- **关联**: E085（musl 缺 pthread_cancel）、E090（meson host_system 不匹配 harmonyos）

## 现象

`conan create libfuse/3.16.1` 编译全绿（16/16 目标），链接期报错：

```text
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by fuse_loop_mt.c
>>> referenced by fuse.c
```

`test_package` 侧同样命中：`test/test_setattr.c:173` 也直接调用 `pthread_cancel`。

## 根因（两条独立机制，必须同时处理）

### 1. OHOS musl libc 不实现 POSIX 线程取消（E085 的具体形态）

`pthread_cancel` / `pthread_setcancelstate` / `pthread_setcanceltype` /
`pthread_testcancel` 四个符号在 OHOS sysroot 里**既不声明也不导出**。
libfuse 依赖其中两个语义：

| 依赖点 | 上游用法 | 缺失后果 |
|--------|----------|----------|
| `lib/fuse.c` LRU 清理线程 | `pthread_cancel(f->prune_thread)` 打断 `sleep()` | 清理线程永不退出，`pthread_join` 挂死 |
| `lib/fuse_loop_mt.c` worker 线程 | `pthread_cancel(w->thread_id)` 把阻塞在 `read()` 的 worker 拽出来 | `fuse_session_loop_mt()` 无法 join worker，卸载时挂死 |

### 2. 「关闭 fd 唤醒阻塞 read」的直觉兜底是错的

很容易想到的替代方案是「主线程 `close(se->fd)`，让 worker 的 `read()` 返回」。
在 OHOS 上**实测不成立**：另一个线程 `close(fd)` 不会唤醒已经阻塞在同一 fd 上的
`read()`，reader 线程一直不返回，`pthread_join` 依然挂死。
（本地用独立的最小 C 程序验证过：reader 阻塞在 `read()`，主线程 `close()` 后
reader 永不返回。）

因此必须在**进入阻塞调用之前**就有一个可被打断的等点。

## 关键坑：meson 的布尔 `configuration_data` 生成**无值** `#define`

探测写好后，C 侧守卫的写法有一个反直觉陷阱：

```meson
private_cfg.set('HAVE_PTHREAD_CANCEL',
        cc.has_function('pthread_cancel', prefix: '#include <pthread.h>'))
```

meson 产出的 `fuse_config.h`：

| 探测结果 | 生成内容 |
|----------|----------|
| 真 | `#define HAVE_PTHREAD_CANCEL`（**没有值**） |
| 假 | `#undef HAVE_PTHREAD_CANCEL` |

所以 `#if HAVE_PTHREAD_CANCEL` 在探测为真时展开成 `# if` → 预处理报错；
**只能**用 `#ifdef` / `#ifndef`。这与 libfuse 自身的 `#ifdef HAVE_SPLICE`
习惯一致，但与 autotools 的 `#define HAVE_X 1` 习惯相反，从 autotools 迁来的
代码最容易踩。

## 推荐方案

**方法**: `meson-feature-detect-plus-bounded-poll-instead-of-cancel`

1. **特性探测而非平台宏**（R8）：在 meson 里用 `cc.has_function()` 产出
   `HAVE_PTHREAD_CANCEL`，C 侧用 `#ifdef/#ifndef` 守卫；不要写
   `#ifdef __OHOS__`，也不要假设「非 Linux 就没有」。
2. **有界 poll 作为可打断等点**：worker 在真正 `read()` 之前先做
   `poll(fd, POLLIN, TIMEOUT_MS)`（100 ms 量级），循环中每次检查
   `fuse_session_exited()`；同时把 channel fd 置 `O_NONBLOCK`，使「poll 返回
   可读但 read 抢不到」的竞态表现为 `-EAGAIN`（当作 continue 处理），
   退出时恢复原 `flags`。
3. **清理线程用停止标志**：`sleep()` 无法被「取消」，改成按 1 秒切片睡眠并在
   每片检查 `prune_thread_stop`（`volatile int`，由停止函数置位），
   再 `pthread_join` 即可正常收敛。
4. **验证方式**：因为没有 `/dev/fuse`，不要试图挂载文件系统；改为在
   `test_package` 里调用 `fuse_session_new()`（不 `mount`）+ `fuse_session_loop_mt()`，
   断言它在**无 channel** 时能自行收敛并返回 `-EBADF`——这条断言正好覆盖
   「无 pthread_cancel 的释放路径不会死锁」。实测约 23 ms 返回。
5. **控制"关闭 fd 兜底"的诱惑**：任何 OHOS 移植里遇到「另一线程阻塞在
   read/accept」的释放问题，都不要指望 `close()` 能唤醒，先建立有界等点。

## 与已有条目的关系

- E085 记录「musl 不实现 pthread_cancel」，本草稿补充**等价实现的落点**与
  「close 不能唤醒 read」这一实测结论。
- E090 记录 meson `host_system` 判定问题；本草稿补充 meson
  `configuration_data` 布尔宏为**无值** `#define` 这一守卫写法陷阱。
- `DRAFT-aml-1.0.0-ohos-pthread-setcancelstate-meson-feature-detect`（aml）与
  `DRAFT-libplctag-2.6.5-ohos-pthread-cancel-android-branch-mirror`（libplctag）
  覆盖的是「**缺哪个符号就守卫哪一句**」的最小补丁形态：aml 在
  `pthread_setcancelstate` 前后加 `#ifdef`，libplctag 把上游既有的 `__ANDROID__`
  分支扩宽成 `__ANDROID__ || __OHOS__`。二者都成立的前提是**没有取消也能正确退出**。
  本草稿覆盖的是这个前提**不成立**的情形：libfuse 的 worker 不能「不做取消就算了」，
  因为取消正是它唯一的退出机制——必须在取消之外**补一个有界等点**，
  否则改动会从「链接失败」退化成「运行期 join 挂死」。这类库（事件循环、
  线程池、需要打断阻塞 syscall 的释路径）不能沿用前两条的最小守卫套路。
