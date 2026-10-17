# libfuse 3.16.1 适配笔记

## 编译环境

- 构建系统: meson
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- Meson: 1.11.0（conan tool_requires）
- 目标: OpenHarmony / HarmonyOS PC (aarch64), os=OHOS
- 状态: built（conan-verify 与 W3 本地 CI 均通过，尚无 CI upload 证据，按 R29 取 built）

## 版本说明

上游**不存在 `fuse-3.16.0`**：GitHub releases 与 tags 列表由 `fuse-3.15.1`
直接跳到 `fuse-3.16.1`（已验证 `fuse-3.16.0.tar.gz` 返回 404）。本次适配按
`3.16.1` 进行，sha256 为
`75a7140ce2d4589eda2784d2279be9d2b273a9b6b0f79ecb871dc4dded046fb5`。

## 编译步骤

```bash
source .build-context-libfuse-3.16.1 && cd $BUILD_SRC_DIR
# // 本地验证（无 conan 环境时的等价命令）
meson setup build --cross-file lf-cross.ini \
  -Dutils=false -Dexamples=false -Dtests=false -Duseroot=false \
  -Ddefault_library=static --prefix=/usr/local
ninja -C build
ninja -C build install
```

配方侧（`conan create`）：`MesonToolchain` 将 `settings.os=OHOS` 映射为
meson `host_machine.system() == 'harmonyos'`，项目选项固定
`utils/examples/tests/useroot = false`，`default_library` 跟随
`options.shared` 默认 `static`（R26）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: error: undefined symbol: pthread_cancel`（lib/fuse.c、lib/fuse_loop_mt.c） | OHOS musl libc 既不声明也不导出 `pthread_cancel` / `pthread_setcancelstate` / `pthread_setcanceltype` / `pthread_testcancel`（E085）。上游用 `pthread_cancel()` 唤醒阻塞在 `read()` 的 worker 线程、并取消 LRU 清理线程 | meson 侧用 `cc.has_function('pthread_cancel')` 产出 `HAVE_PTHREAD_CANCEL`；C 侧以 `#ifdef/#ifndef` 守卫，缺 API 时改用**有界 poll + 退出标志**（补丁 0001/0002/0004） |
| 2 | `lib/meson.build` 选择了 BSD 挂载后端 | 上游写死 `host_machine.system().startswith('linux')`，OHOS 上报 `harmonyos`，条件不成立而落到 `mount_bsd.c`（E090） | 补丁 0003 改为 `startswith('linux') or == 'harmonyos'`，OHOS 基于 Linux 内核，Linux 挂载后端适用 |
| 3 | 「关闭 fd 唤醒阻塞 read」的兜底方案会死锁 | 实测 OHOS 上另一线程 `close(fd)` **不会**唤醒已阻塞在同一 fd 上的 `read()`（`pthread_join` 永久阻塞） | 放弃 close 兜底：worker 先对 channel 做 100 ms 有界 `poll()`，主循环再把 `se->fd` 置 `O_NONBLOCK` 并处理 `-EAGAIN`，退出时恢复原 flags |
| 4 | `#if HAVE_PTHREAD_CANCEL` 写法在探测为真时预处理报错 | meson 的 `configuration_data.set()` 对布尔真写出**无值** `#define HAVE_X`（假写出 `#undef HAVE_X`），`#if HAVE_X` 展开为空表达式 | 全部改用 `#ifdef HAVE_X` / `#ifndef HAVE_X`（与上游自身 `#ifdef HAVE_SPLICE` 惯例一致） |
| 5 | `ninja` 归档 `libfuse3.a` 时报 `/bin/sh: safe-bin/rm: No such file or directory`（code=126） | 宿主沙箱的 `rm` 垫片 shebang 指向不存在的 `/bin/bash` | 本地验证时在 PATH 前置一个转发到 `/usr/bin/rm` 的 `rm` 垫片；CI 侧不受影响 |
| 6 | meson `tests=true` 时 `test/test_setattr` 链接失败（`undefined symbol: pthread_cancel`） | 上游测试程序自己也直接调用了 `pthread_cancel` | 不启用 `tests`（该目录的所有程序都需要真实挂载 FUSE，无法在 OHOS 运行）；**未修改任何上游测试文件** |

## 源码修改

| 文件 | 修改 | 机制 |
|------|------|------|
| `meson.build` | 新增 `private_cfg.set('HAVE_PTHREAD_CANCEL', cc.has_function('pthread_cancel', prefix: '#include <pthread.h>'))` | 特性探测（非平台宏），补丁 0004 |
| `lib/meson.build` | `host_machine.system().startswith('linux') or host_machine.system() == 'harmonyos'` → `mount.c` | 补丁 0003 |
| `lib/fuse_loop_mt.c` | 新增 `fuse_loop_wait_for_input()`（`#ifndef HAVE_PTHREAD_CANCEL`，100 ms 有界 `poll()`）；`fuse_do_work()` 守卫 `pthread_setcancelstate` 并在无 cancel 时用 poll 判退；`fuse_session_loop_mt_312()` 对 `se->fd` 置 `O_NONBLOCK` 并处理 `-EAGAIN`，退出后恢复 flags | 补丁 0002 |
| `lib/fuse.c` | `struct fuse` 增 `volatile int prune_thread_stop`；`fuse_prune_nodes()` 以 1 秒切片睡眠并检查标志；`fuse_stop_cleanup_thread()` 在无 cancel 时置标志而不是 `pthread_cancel` | 补丁 0001 |

补丁清单（conandata.yml）：

| 补丁 | 内容 |
|------|------|
| `0001-lib-fuse.c.patch` | LRU 清理线程以停止标志退出（无 `pthread_cancel` 时） |
| `0002-lib-fuse_loop_mt.c.patch` | 多线程 loop 以有界 poll 释放 worker（无 `pthread_cancel` 时） |
| `0003-lib-meson.build.patch` | OHOS（`harmonyos`）选用 Linux 挂载后端 |
| `0004-meson.build.patch` | 探测 `pthread_cancel` 是否可用 |

全部补丁走 `refresh-patch --auto` 生成，无平台宏（R8 默认口径）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| meson | 1.11.0 | `tool_requires`，构建系统本体 |
| （无运行时依赖） | — | 上游仅需 libc + pthread，OHOS 已内建 |

## 上游测试清点（R51 三步法）

适配前清点（源码树 `libfuse-3.16.1/test/`）：

| 类别 | 数量 | 具体条目 |
|------|------|----------|
| meson 注册用例 | 1 | `wrong_command`（`test/meson.build` 中 `test()` 注册；非 subproject 时设计为返回 1，只用于提示改用 pytest） |
| C 测试程序 | 5 | `test_syscalls.c`、`test_setattr.c`、`test_write_cache.c`、`readdir_inode.c`、`release_unlink_race.c` |
| pytest 模块 | 3 | `test_examples.py`、`test_ctests.py`、`test_custom_io.py`（由 `test/ci-build.sh` → `python3 -m pytest test/` 驱动） |

实际可否运行：**否**，逐项技术原因：

1. 所有 C 测试程序与 pytest 模块的功能断言都发生在**已挂载的 FUSE 文件系统**上
   （`fuse_session_mount()` / `fusermount` / 真实 `/dev/fuse`）；OHOS 用户态不暴露
   `/dev/fuse`，`fuse_session_mount()` 无法成功，测试在准备阶段即失败。
2. `test_setattr.c:173` 直接调用 `pthread_cancel()`，OHOS libc 无此符号（E085），
   链接期即 `undefined symbol`。
3. `meson test` 唯一注册的 `wrong_command` 在非 subproject 构建下**设计为返回 1**
   （源码注释：「This is not the command you are looking for. You probably want to
   run 'python3 -m pytest test/'」），因此 `meson test` 必然失败，不能作为上游测试入口。

采取的措施：未启用 `tests`、未修改任何上游测试文件；改为在 `test_package/` 用
**真实消费者程序**覆盖公共 API 与本次适配的两条关键路径（LRU 清理线程启停、
多线程 session loop 收敛），共 14 条断言。

## 验证结果

```bash
$ clang -D_FILE_OFFSET_BITS=64 -I<stage>/usr/local/include test.c -o test_libfuse \
      <build>/lib/libfuse3.a
$ ./test_libfuse
PASS: fuse_version() matches the headers it was built against
PASS: fuse_version() is 316 (libfuse 3.16.1)
PASS: fuse_opt_add_arg() accepted the program name
PASS: fuse_opt_add_arg() accepted --tag=ohos
PASS: fuse_opt_parse() consumed the custom option table
PASS: fuse_opt_parse() stored the --tag argument value
PASS: fuse_opt_parse() removed the consumed argument
PASS: fuse_new() created a FUSE object
PASS: fuse_start_cleanup_thread() started the LRU pruner
PASS: fuse_stop_cleanup_thread() joined the LRU pruner
PASS: fuse_destroy() released the FUSE object
PASS: fuse_session_new() created a low-level session
PASS: fuse_session_loop_mt() terminated and reported the missing channel
PASS: fuse_session_destroy() released the session
test libfuse 3.16.1: PASSED (0 failure(s))
```

真机（OHOS aarch64）交叉编译与运行均通过：`libfuse3.a` 16/16 目标编译成功，
`llvm-nm` 确认归档内无 `pthread_cancel` 残留引用，`mount.c.o`（而非
`mount_bsd.c.o`）已编入。`fuse_session_loop_mt()` 在无 channel 时约 23 ms 内
返回 `-EBADF`，证明无 `pthread_cancel` 的释放路径不会死锁。

## 注意事项

- `fuse_session_loop_mt()` 在未挂载时返回 `-EBADF` 属**预期**行为（无 channel
  描述符），测试据此断言。
- 本次不打包 `util/`（`fusermount`、`mount.fuse`）：它们依赖 `/etc/mtab` 与
  udev 规则，且需要 setuid/root 才能工作。软件级 `commands.json` 仍只登记
  2.9.9 提供的 `fusermount` / `ulockmgr_server`（R38 只要求对实际产物声明）。
- **提交前必须核对 `conandata.yml`**：W3（`ci/conan/build_and_test.sh`）的
  Pre-download 备份取在镜像回退改写**之后**，因此其 EXIT 陷阱虽然打印
  「conandata.yml 已还原为官方 URL」，实际写回的却是镜像列表（本次为
  `gh-proxy.com` 前置）。W3 全绿、`conan-verify` 全绿都与该污染并存，只有
  `git diff` 能发现。已人工还原为官方单值 URL 并清理
  `conandata.yml.ghfast-bak` / `conandata.yml.orig` 残留。
  详见知识草稿 `DRAFT-LIBFUSE-3161-W3-PREDL-MIRROR-RESTORE-POLLUTES-CONANDATA`。
---

**编译结束**: 2026-09-28 00:24
**最终状态**: built
