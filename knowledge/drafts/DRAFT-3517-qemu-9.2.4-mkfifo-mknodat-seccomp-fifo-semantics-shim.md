# DRAFT-3517-qemu-9.2.4-mkfifo-mknodat-seccomp-fifo-semantics-shim

> HarmonyOS PC（aarch64-linux-ohos）的进程处于 seccomp 过滤下，`mkfifo(3)`
> 经 `mknodat(2)` 被全域拒绝；本条目给出 FIFO 语义的用户态模拟方法，以及
> **fortify `__open_chk` 使「open 垫片」静默失效**这一必踩陷阱。
> 来自 qemu 9.2.4 适配（Issue #3517 / PR !13119）。

## 现象

qemu 的 `tests/qtest/qmp-test.c` 用 FIFO 制造「阻塞中的 in-band QMP 命令」：
setup 时 `g_dir_make_tmp` + `mkfifo`，随后下发 `blockdev-add`（配 blkdebug，
其配置文件由该 FIFO 提供，QEMU 会 `fopen` 并**真实阻塞**），解除时对 FIFO
写端 `open` + `close`，让读端 `read` 收到 EOF 从而完成命令。测试随后断言
「带外的命令追上了被阻塞的命令」，因此**阻塞必须真实发生**。

本机上该用例直接 `g_error("mkfifo: ...")` 退出；若把 setup 跳过，则在

```
ERROR:../src/tests/qtest/qmp-test.c:212:unblock_blocked_cmd:
      assertion failed (fd >= 0)
```

处失败。注意报告位置是「解除阻塞」，不是「创建 FIFO」，两个报错都不带
「FIFO 不可用」字样。

## 根因

1. **系统调用级拒绝，换目录无解**。查 `/proc/self/status` 实测：

```
Seccomp: 2
CapEff: 000000000000002a      <- 不含 CAP_MKNOD(1<<27)
```

   `mkfifo(3)` 走 `mknodat(2)`。对 `$HOME`、`$TMPDIR`、HMDFS、`/dev/shm`、
   `/tmp`、系统目录逐一实测，`mknodat(AT_FDCWD, p, S_IFIFO|0600, 0)` 全部
   失败（EPERM，个别目录 EACCES）。因为是**沙箱过滤**而非文件系统能力差异，
   任何目录都不可用。

2. **垫片会被 fortify 绕过**（第二个陷阱）。上游二进制以
   `_FORTIFY_SOURCE` 编译，两参数形式的 `open(fifo, O_WRONLY)` 在**重定位表**
   中解析为 **`__open_chk`** 而非 `open`：

```
$ llvm-objdump -R tests/qtest/qmp-test | grep open
...  __open_chk
```

   只拦 `open`/`open64` 的实现会被绕过 → writer 拿到 `ENOENT`（FIFO 只存在于
   内存映射中）→ 断言依旧失败，且现象是「垫片似乎没生效」。同理读端若用
   `fopen()`，其内部走 libc 内部 `open`，必须单独拦 `fopen`/`fopen64`。

3. **`__open_chk` 的签名由 sysroot 决定**。本机
   `fortify/fcntl.h` 声明的是**两参数**形式：

```c
int __open_chk(const char *, int);
```

   带 `mode` 的重载改走 `__open_real`（即普通 `open` 符号）。若按可变参数
   `int __open_chk(const char *, int, ...)` 定义，会与头文件声明冲突而**编译
   失败**。

## 修复

抽象 AF_UNIX 套接字（OHOS 可用）模拟 FIFO 语义：

| FIFO 语义 | 模拟实现 |
|---|---|
| 路径 → 名字 | 纯函数派生（多进程免协调，写端由被测程序 spawn） |
| 读端 open 阻塞至有写端 | `bind` + `listen` + `accept()`（accept 天然阻塞） |
| 写端 open 阻塞至有读端 | `connect()`，对 `ECONNREFUSED`/`ENOENT` 重试 |
| 写端 close → 读端 EOF | 套接字关闭即 EOF（与 FIFO 一致） |
| `mkfifo` 创建节点 | 直接返回成功（不建节点） |
| `unlink` | 直接返回成功 |

必须**成对**拦截的入口：

```
mkfifo
open  open64  openat  openat64
__open_chk  __openat_chk  __open64_chk  __openat64_chk
fopen  fopen64
```

并用环境变量（`QTEST_FIFO_SHIM=1`）与**路径形状**双重门禁，避免影响非目标路径。

## 验证

| 场景 | 结果 |
|---|---|
| 独立探针（mkfifo → 写端 open 后读端 EOF） | 基线 `mkfifo FAIL`；垫片下 `mkfifo=OK`、写端 `open=3`、读端立即 EOF |
| `qmp-test`（arm + aarch64） | 由 ERROR 转为 **4/4 通过** |
| `test-io-channel-command`（另需 socat，其 `PIPE:` 地址自身也调 `mkfifo`） | 由 SKIP 转为 **4/4 通过** |

## 适用边界

- 垫片是**本地验证 harness，不随配方发布**。
- 语义等价面：阻塞性 open、EOF 时机、单向数据流。
- **不等价面**：`stat()`（无 inode）、权限与属主、`O_NONBLOCK`、
  多写端/多读端语义、`poll`/`select` 对 FIFO 的特定行为。依赖这些的用例
  不能靠本垫片。
- 配方侧的有意取舍：本包**不**把 `socat` 纳入依赖。虽然制品仓有
  `socat/1.7.4.4.1`、本地接入后 `test-io-channel-command` 可 4/4 通过，但该
  测试自身调用 `mkfifo(3)`——CI 无垫片，加依赖会使该测试**由 SKIP 变为硬
  失败**，故保持 SKIP 并在声明文件中如实注明。
