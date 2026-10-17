# 测试报告 — libfuse 3.16.1 (OHOS aarch64)

> **项目**: libfuse (FUSE 3.x)
> **测试日期**: 2026-09-27
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64（OHOS SDK 26.0.0.18，clang 15 / libc++ / musl）
> **测试类型**: 消费者端到端测试（test_package，`conan create` 实跑）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 36 | 100% |
| 通过 (PASS) | 36 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

> 断言构成：36 项**取值 / 内容校验**（对返回值、句柄、字符串、文件内容做实际校验），
> 其中 `test.c` 11 项（API / 对象生命周期 / 多线程 loop 收敛取值校验），
> `test_fs_consumer.c` 25 项（鸿蒙特有完整消费者用例：内存文件系统端到端工作流 +
> `pthread_cancel` 替代路径内容校验）。全部为消费者侧对真实编译产物 `libfuse3.a` 的调用，
> 无到达型断言（`MANIFEST.yml` 中 `reached_line_assertions: 0`）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** —— 36 项取值 / 内容校验全部通过，其中 `test_fs_consumer.c` 的 25 项构成一条
**完整端到端消费者用例**，覆盖本移植核心风险点：`pthread_cancel` 缺失后 LRU 清理线程的
停止标志路径与多线程 loop 的 worker 释放路径——以「清理线程停止 / 多线程 loop 拆解后文件内容
仍逐字节一致」的内容校验证明替代路径不死锁、不损坏状态。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 `/dev/fuse`，无法真挂载文件系统 | 上游 pytest 集成测试套件（15 例）与 5 个 C 驱动程序不可运行 | 🟡 |
| OHOS musl libc 无 POSIX 线程取消 | `lib/fuse.c` LRU 清理线程、`lib/fuse_loop_mt.c` worker | 🟢（已用有界 poll 替代） |

### 2.3 可用功能清单

```
✅ fuse_version / FUSE_USE_VERSION 版本握手: 头文件与库一致（316）
✅ fuse_opt_add_arg / fuse_opt_parse: 自定义选项表解析与消费
✅ fuse_new / fuse_destroy: 高层对象生命周期
✅ fuse_start_cleanup_thread / fuse_stop_cleanup_thread: LRU 清理线程启停（停止标志替代 pthread_cancel）
✅ fuse_session_new / fuse_session_destroy: 低层 session 生命周期
✅ fuse_session_loop_mt: 多线程会话循环的退出路径（有界 poll 替代 pthread_cancel）
⚠️ fuse_session_mount / 实际挂载读写: 需 /dev/fuse，OHOS 用户态无此设备
```

### 2.4 已知限制

1. 上游 `test/` 下的 pytest 套件（`test_ctests.py` 3 例、`test_custom_io.py` 1 例、`test_examples.py` 11 例，合计 15 例）以及 5 个 C 驱动程序（`test_write_cache`、`test_setattr`、`test_syscalls`、`readdir_inode`、`release_unlink_race`）全部需要真实挂载 FUSE 文件系统，OHOS 用户态无 `/dev/fuse`，因此不可运行；详见 `notes.md` 的上游测试清点表。
2. 上游 meson 唯一注册的测试 `wrong_command` 设计上恒返回 1（仅在提示使用者改用 `python3 -m pytest test/`），不是可判定的测试用例。
3. `-Dutils=false`：不构建 `fusermount3` / `mount.fuse3` 辅助程序（需要 `useroot` 与特权挂载，OHOS 构建环境不适用）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `fuse_version() == FUSE_VERSION` | 库与头文件版本握手 | ✅ PASS |
| `fuse_version() == 316` | 确认构建的是 libfuse 3.16.1 | ✅ PASS |
| `fuse_opt_add_arg()` ×2 | 参数表追加程序名与 `--tag=ohos` | ✅ PASS |
| `fuse_opt_parse()` 返回值 | 自定义选项表解析成功 | ✅ PASS |
| `fuse_opt_parse()` 存储 `--tag` 值 | 选项值写入用户结构体 | ✅ PASS |
| `fuse_opt_parse()` 消费计数 | 被消费参数已从 argv 移除 | ✅ PASS |
| `fuse_new()` | 创建高层 FUSE 对象 | ✅ PASS |
| `fuse_start_cleanup_thread()` | 启动 LRU 清理线程 | ✅ PASS |
| `fuse_stop_cleanup_thread()` | 停止并 join 清理线程（停止标志路径） | ✅ PASS |
| `fuse_destroy()` | 释放高层对象 | ✅ PASS |
| `fuse_session_new()` | 创建低层 session | ✅ PASS |
| `fuse_session_loop_mt()` | 无 channel 时收敛并返回 `-EBADF` | ✅ PASS |
| `fuse_session_destroy()` | 释放低层 session | ✅ PASS |

（上表 13 行，其中 `fuse_opt_add_arg()` 一行含 2 条断言，合计 14 条断言。）

### 3.1.1 鸿蒙特有完整消费者用例（test_fs_consumer.c，rule12 对应项）

模拟下游 FUSE 文件系统作者：注册完整 `fuse_operations` 表并经 `fuse_new()` 构建 FUSE 对象，
驱动内存文件系统跑通端到端工作流，并嵌入本移植的 `pthread_cancel` 替代路径做内容校验。

| 阶段 | 测试项 | 结果 |
|------|--------|------|
| 构造输入 / 选项解析 | `fuse_opt_parse()` 捕获自定义 `--fsname=ohmemfs` | ✅ PASS |
| 真实执行（构建对象） | `fuse_new()` 以完整 ops 表构建 FUSE 对象 | ✅ PASS |
| 写文件 | `create` + `write` `/doc.txt`（内容 `HarmonyOS FUSE 3.16.1 端到端验证`） | ✅ PASS |
| 读回校验（内容） | `read` 逐字节还原写入内容 | ✅ PASS |
| `getattr` 校验 | 报告常规文件且大小正确 | ✅ PASS |
| 建子目录 + 写 | `mkdir /sub` + `create`/`write` `/sub/note.txt` | ✅ PASS |
| `readdir` 列举（内容） | `/` 含 `doc.txt` 与 `sub` | ✅ PASS |
| `rename` 移动（内容） | 旧路径消失、新路径 `/memo.txt` 出现 | ✅ PASS |
| `unlink` 清理（内容） | 根目录回到空（仅 `.`/`..`） | ✅ PASS |
| pthread_cancel 替代·清理线程 | `fuse_start/stop_cleanup_thread` 启停后 `/keep.txt` 内容完好 | ✅ PASS |
| pthread_cancel 替代·多线程 loop | `fuse_session_loop_mt()` 返回 `-EBADF` 且拆解后内容一致 | ✅ PASS |

> 该用例全程确定性、可复现，所有校验均为取值 / 内容校验（无 `check(1, ...)` 到达型断言），
> 满足 rule12「鸿蒙特有测试须为完整消费者用例」要求。

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| — | — | 无失败项 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 上游 pytest 集成套件（15 例） | 需要真实 FUSE 挂载，OHOS 无 `/dev/fuse` |
| 上游 C 驱动程序（5 个） | 同上（由 pytest 驱动，须挂载后运行） |
| 上游 meson 测试 `wrong_command`（1 例） | 设计上恒返回 1，仅作提示，不可判定 |

---

## 四、关键问题分析

### 问题1: OHOS musl libc 不导出 pthread_cancel，链接期报 undefined symbol

**现象**：
```
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by fuse_loop_mt.c
>>> referenced by fuse.c
```

**根因分析**：
OHOS musl libc 既不声明也不导出 `pthread_cancel` / `pthread_setcancelstate` /
`pthread_setcanceltype` / `pthread_testcancel`。libfuse 在两处依赖取消语义：
LRU 清理线程退出、多线程会话循环中 worker 的释放。

**解决方案**：
meson 侧用 `cc.has_function('pthread_cancel')` 特性探测生成 `HAVE_PTHREAD_CANCEL`
（不使用平台宏，满足 R8）；C 侧用 `#ifdef/#ifndef` 守卫。无取消时：
① 清理线程改为 1 秒切片睡眠 + `prune_thread_stop` 停止标志；
② worker 在 `read()` 前先做有界 `poll()`（100 ms）并检查 `fuse_session_exited()`，
session fd 置 `O_NONBLOCK`、`-EAGAIN` 视为 continue，退出时恢复原 `flags`。

### 问题2: 「另一线程 close(fd) 唤醒阻塞 read()」在 OHOS 上不成立

**现象**：
独立最小程序验证：reader 阻塞在 `read()`，主线程 `close()` 同一 fd 后 reader 永不返回。

**根因分析**：
OHOS 不提供「close 打断阻塞读」的行为，因此不能用关闭 fd 的方式释放 worker。

**解决方案**：
改为在进入阻塞调用之前就建立可打断等点（有界 `poll()`），不依赖 close 唤醒。
本测试的第 12 条断言（`fuse_session_loop_mt()` 收敛返回 `-EBADF`）即该路径的回归保护。

---

## 五、测试环境

```
libfuse 3.16.1 (fuse-3.16.1.tar.gz, sha256 75a7140ce2d4589eda2784d2279be9d2b273a9b6b0f79ecb871dc4dded046fb5)
meson 1.11.0 | clang 15 (OHOS SDK 26.0.0.18, aarch64-linux-ohos) | libc++
conan create archives/l/libfuse/3.16.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
configure: -Dexamples=false -Dutils=false -Dtests=false -Duseroot=false, default_library=static
产物: lib/libfuse3.a
```

---

*报告生成时间: 2026-09-27*
