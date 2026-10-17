# tevent 0.17.1 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://tevent.samba.org/ |
| 版本 | 0.17.1（standalone tarball，自带 lib/replace、lib/talloc、third_party/cmocka） |
| 源码 | `https://download.samba.org/pub/tevent/tevent-0.17.1.tar.gz` |
| SHA256 | `1be2dea737cde25fe06621f84945e63eb71259e0c43e9f8f5da482dab1a7be92` |
| 构建 | direct-cc（直接驱动 clang，绕开上游 waf） |
| 包类型 | static-library（`libtevent.a` + `include/tevent.h`） |
| 依赖 | `talloc/2.4.4`（已发布，tevent.h 公共头 include `<talloc.h>`，故 transitive） |

## 2. 为什么不用上游 waf

tevent standalone tarball 的构建入口是 `./configure && make`（waf）。在 OHOS
worker 上不可直接用：

1. `wscript configure()` 会 `RECURSE('lib/replace')` 并跑 wafsamba 的
   **mandatory** 运行探针，这些探针需要可写的 `/tmp`，在只读 /tmp 或权限
   归一化（HMDFS）的环境下直接失败；
2. `lib/replace` 的完整 autoconf 特性矩阵（`AC_LIBREPLACE_NETWORK_CHECKS`
   等）在 waf 之外无法复现，`replace.c` 单独编译会报
   `"AC_LIBREPLACE_NETWORK_CHECKS missing in configure"`；
3. `configure` 还会调用 `SAMBA_CHECK_PYTHON/HEADERS` 与
   `CHECK_FOR_THIRD_PARTY`，引入与本包无关的 Python/CMocka 探测分支。

因此本配方抄 samba 家族在仓库中的既有做法（参见 `archives/t/talloc/2.4.4`），
用 direct-cc 直接编译，宏集合固定写死在 `conanfile.py` 的 `COMMON_DEFINES`。

## 3. 源文件清单

上游 `wscript build()` 的 SRC 列表共 14 个文件，`HAVE_EPOLL` 时追加
`tevent_epoll.c`。OHOS 有 `sys/epoll.h`，**必须**把 `tevent_epoll.c` 编进去：
漏掉时 tevent 会静默退化到 poll 后端（事件循环仍能跑，但语义/性能不同，
且 `tevent_backend_list()` 里不会出现 `epoll`）。

```
tevent.c tevent_debug.c tevent_fd.c tevent_immediate.c tevent_queue.c
tevent_req.c tevent_wrapper.c tevent_poll.c tevent_threads.c tevent_signal.c
tevent_standard.c tevent_timed.c tevent_util.c tevent_wakeup.c tevent_epoll.c
```

## 4. 踩坑与解决

### 4.1 `sys_errlist` 未定义（链接期）

**现象**

```
ld.lld: error: undefined symbol: sys_errlist
>>> referenced by tevent.c tevent.o:(tevent_common_loop_wait)
>>> referenced by tevent_epoll.c tevent_epoll.o:(epoll_event_context_init)
>>> referenced 9 more times
```

**根因**：`lib/replace/replace.h:208` 有

```c
#ifndef HAVE_STRERROR
extern const char *const sys_errlist[];
#define strerror(i) sys_errlist[i]
#endif
```

tevent 各处 `strerror(errno)` 全被重映射到 glibc/BSD 遗留的 `sys_errlist[]`
数组，而 OHOS 的 libc 不导出该符号。

**解决**：定义 `-DHAVE_STRERROR`，让 replace.h 走真实 `strerror()`。

### 4.2 `rep_strerror_r` 悬空声明

`replace.h:645` 的条件是

```c
#if (!defined(HAVE_STRERROR_R) || !defined(STRERROR_R_XSI_NOT_GNU))
#define strerror_r rep_strerror_r
int rep_strerror_r(int errnum, char *buf, size_t buflen);
#endif
```

只定义 `HAVE_STRERROR_R` 并不够——它仍然会把 `strerror_r` 重映射到一个本包
没有实现的 `rep_strerror_r`。两个宏同时定义才能既不重映射、也不留悬空声明。

### 4.3 `rep_memset_s` 未定义

**现象**

```
ld.lld: error: undefined symbol: rep_memset_s
>>> referenced by tevent_signal.c tevent_signal.o:(tevent_common_add_signal)
```

**根因**：`replace.h:994` 有 `#define memset_s rep_memset_s`，
`ZERO_STRUCT` / `BURN_DATA` 宏展开后会调用它。`tevent_signal.c` 与
`tevent_epoll.c` 都用到。上游实现位于 `lib/replace/replace.c:960`，但
`replace.c` 单独编译必然失败（缺 `AC_LIBREPLACE_NETWORK_CHECKS`、
`HAVE_FTRUNCATE`、`struct tm` 完整定义……）——它是为 waf 生成的全量
`config.h` 编写的。

**解决**：`files/tevent_ohos_compat.c` 只提供这一个符号，语义与上游逐行对齐
（`dest == NULL` → `EINVAL`；`destsz`/`count` 超 `RSIZE_MAX` 或 `count >
destsz` → `ERANGE` 且仍按 `destsz` 清零；否则写 `count` 字节返回 0），
并用 `volatile` 指针写入，等价于上游
`HAVE_GCC_VOLATILE_MEMORY_PROTECTION` 分支里那条 `__asm__ volatile` 屏障，
保证清零不会被优化掉。这一点对 `BURN_DATA`（擦除口令等敏感数据）是必要的。

### 4.4 `TEVENT_NUM_SIGNALS`

上游 `wscript configure()`：

```python
tevent_num_signals = 64
tevent_num_signals = max(tevent_num_signals, NSIG, _NSIG, SIGRTMAX, SIGRTMIN * 2)
```

OHOS：`_NSIG = 65`、`NSIG = _NSIG`；而 `SIGRTMIN`/`SIGRTMAX` 展开为运行时
函数 `__libc_current_sigrtmin()/__libc_current_sigrtmax()`，waf 的
`CHECK_VALUEOF` 无法把它折叠成编译期常量（探针会失败 → 返回 None）。
最终取 **65**。

### 4.5 cmocka 的 `uintptr_t` 重定义

上游 `third_party/cmocka/cmocka.h` 在 musl 上会重复 `typedef uintptr_t`。
这是上游 cmocka 的既知问题（它对 `_UINTPTR_T` 的守卫不完整），
只需在测试编译命令上补 `-D_UINTPTR_T`，不需要改上游头文件。

### 4.6 `test_tevent_trace` 的两个 fd 用例要求 fd 0 可写

**现象**（CI 上 `conan create` 倒在 `build()`）：

```
test: test_trace_event_fd__loop
failure: test_trace_event_fd__loop [
tctx->before_handler
.../b/tests/test_tevent_trace.c:436: error: Failure!
]
...
test: test_trace_event_fd__free_in_handler
failure: test_trace_event_fd__free_in_handler [
tctx->before_handler
.../b/tests/test_tevent_trace.c:529: error: Failure!
]
```

`test_tevent_trace` 的 24 个用例里只有这两个挂；同文件的
`test_trace_event_fd__reset` / `__free`（只挂不 loop）以及
timer/signal/immediate 的 `__loop` 变体全绿。

**根因**：这两个用例写死了 fd 0 ——

```c
fde = tevent_add_fd(tctx->ev, tctx, 0, TEVENT_FD_WRITE, fd_handler, tctx);
...
TEVENT_FD_WRITEABLE(fde);          /* 与 add 时的 TEVENT_FD_WRITE 相同，实际是空操作 */
tevent_loop_once(tctx->ev);
assert_true(tctx->before_handler); /* 第 436 行 */
```

即"把 fd 0 当成一个可写事件来派发"，断言 trace 回调确实走到了
`TEVENT_EVENT_TRACE_BEFORE_HANDLER`（`tevent_fd.c:173`）。
epoll 后端只有在 fd 0 **真的可写**时才会得到 `EPOLLOUT`。上游 CI 里
stdin 是控制终端（永远可写），所以上游一直绿；本仓库 CI worker / builder
容器里 stdin 是一根已经 EOF 的管道，内核只上报 `EPOLLHUP`：

```
epoll_ctl(3, EPOLL_CTL_ADD, 0, {events=EPOLLOUT, data=...})            = 0
epoll_wait(3, [{events=EPOLLHUP, data=...}], 1, 30000)                 = 1
```

`tevent_epoll.c` 走 `EPOLLHUP|EPOLLERR|EPOLLRDHUP` 分支时，只有在
`effective_flags` 里带了 `TEVENT_FD_READ`（或 `TEVENT_FD_ERROR`）才会往
`flags` 里塞东西；本用例只注册了 WRITE，于是 `flags == 0`，
`tevent_common_fd_mpx_select()` 返回 `NULL` → `continue`，
handler 从不被调用 → `before_handler` 断言炸掉。

**这不是本配方的缺陷，也不是 OHOS 特有**：把同一份源码 + 同一套
`COMMON_DEFINES` 在一台 x86-64 Linux 上按配方原样编译，用
`./test_tevent_trace`（stdin = EOF 管道）复现出**逐字节相同**的两处失败；
换 `./test_tevent_trace </dev/null` 立刻全绿。差异只在 fd 0 指向什么。

**解决**：配方在 `_run_upstream_tests()` 里以 `"<binary>" < /dev/null`
运行 —— `/dev/null` 是永远就绪的字符设备，poll 恒报 `POLLIN|POLLOUT`，
于是"fd 0 可写"这个前提在无 tty 的环境里照样成立，两个用例的断言仍然
是真的被事件循环驱动起来、真的全跑过（不是跳过、不是屏蔽）。
不改上游测试源码，也不减少执行用例数。

## 5. 上游测试

上游 `wscript test()` 目标共三项：

| 测试 | 类型 | 处置 |
|------|------|------|
| `tests/test_tevent_tag.c` | cmocka 单测（5 个用例 / 24 处断言） | build() 内编译 + 运行 |
| `tests/test_tevent_trace.c` | cmocka 单测（24 个用例 / 425 处断言） | build() 内编译 + 运行（stdin 接 /dev/null，见 §4.6） |
| `bindings.py` | pytevent CPython 扩展的 Python 测试 | **排除**：本配方是纯 C 包，不构建 `_tevent.so` 扩展（OHOS 构建机上没有 Python 开发头） |

测试用 cmocka 来自源码树内的 `third_party/cmocka/cmocka.c`（与上游一致，
不引入外部 cmocka 包），编译后只在 build 阶段使用，**不进包**。

源码根目录另有 `test_req.c` / `testsuite.c`，但 `wscript` 的
`build()`/`test()` 都没有引用它们（`test()` 里只有一句注释说明
the tevent testsuite is part of smbtorture in samba4），因此不算上游测试目标。

`conan create` 的 test 阶段另外由 `test_package/test_tevent.c` 覆盖消费者
视角：断言 `tevent_backend_list()` 含 `epoll`、`tevent_context_init()` 可用、
immediate/timer/fd 三类事件各投递一次、从管道读到写入的字节、事件循环有界收敛、
`talloc_free()` 能连 context 一起释放。

## 6. 验证记录

本地用 OHOS native SDK（clang 15.0.4 + `--target=aarch64-linux-ohos`）预验证：
15 个 `tevent*.c` + compat 全部零告警编译通过，`libtevent.a` 成档后
`test_tevent_tag` / `test_tevent_trace` 均能链接成功，`llvm-nm -u` 显示
归档内除 libc/pthread 外只剩 tevent 自身跨对象符号、`talloc_*` 与
`rep_memset_s`（由 compat 提供）。

CI（OHOS aarch64 原生 worker）中 `conan create` 会真正编译并**运行**两个
cmocka 单测与 test_package 消费者测试。

本地另做了一次 x86-64 Linux（gcc 11.4）端到端复跑，按配方原样编译
`lib/talloc/talloc.c` + 15 个 `tevent*.c` + `files/tevent_ohos_compat.c`，
链接 `third_party/cmocka` 与两个测试二进制后实跑：

```
$ ./test_tevent_tag   </dev/null   → 5 Tests 0 Failures   (exit 0)
$ ./test_tevent_trace </dev/null   → 24 Tests 0 Failures  (exit 0)
```

同一对二进制在 stdin 是 EOF 管道时，`test_tevent_trace` 恰好复现
§4.6 描述的两处失败 —— 以此确认改动是"给 fd 0 一个可写描述符"，
而不是"屏蔽了一个只在 OHOS 上出现的问题"。

## 7. test_package 断言清单

`test_package/test_tevent.c` 共 6 处可观测行为断言，失败时以不同退出码
（2…14）区分，便于 CI 日志定位：

| # | 断言 | 失败退出码 |
|---|------|-----------|
| 1 | `tevent_backend_list(mem_ctx)` 含 `epoll`（后端未静默退化到 poll） | 2 |
| 2 | `tevent_context_init(mem_ctx)` 成功非空 | 3 |
| 3 | immediate 事件经 `tevent_loop_once()` 投递且**恰好一次** | 4–5 |
| 4 | `tevent_add_timer` 到期事件恰好一次 | 6–7 |
| 5 | `tevent_add_fd` 注册的真实 pipe 可读，读到字节 `'H'` | 8–11 |
| 6 | `tevent_loop_once()` 有界收敛（1000 轮内事件投递完毕） | 12–13 |

末尾 `talloc_free(mem_ctx)` 验证 tevent context 随根内存一并释放（失败退出码 14）。

第 1 条是本包 direct-cc 路线下唯一的「后端身份」守卫：漏编 `tevent_epoll.c`
不会编译报错，只会让该断言失败，把一次静默的性能/语义回退变成一次显式测试失败。

## 8. 卸载/回退

若未来需要升级，注意 `COMMON_DEFINES` 中每一项都对应 replace.h/wscript
中的一个探测结果，升级时应对照上游 `lib/replace/replace.h` 与
`wscript configure()` 重新核对新增的 `HAVE_*` 守卫。
