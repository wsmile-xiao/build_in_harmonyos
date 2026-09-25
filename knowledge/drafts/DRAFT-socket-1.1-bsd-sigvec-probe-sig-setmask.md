# socket 1.1 — 用 `SIG_SETMASK` 探测 BSD 信号 API，OHOS/musl 必然选错分支（draft）

**Category**: portability | libc | signal | ohos · **Severity**: 3 · **Tool**: clang/make/conan

## 症状

交叉编译到 aarch64-linux-ohos 时，`utils.c` 的信号初始化函数直接编译失败：

```text
utils.c:76:25: error: variable has incomplete type 'struct sigvec'
    static struct sigvec svec = { exitsig, ~0, 0 } ;
                         ^
utils.c:76:12: note: forward declaration of 'struct sigvec'
utils.c:106:6: warning: call to undeclared function 'sigvec'
```

socket 1.1 共 2 处（结构体定义 + 调用点），都在 `init_signals()` 里。
（2026-09-21 实测，OHOS NDK clang，`make targets`。）

## 根因

1. 源码用 `#ifdef SIG_SETMASK /* only with BSD signals */` 判断「本机是不是 BSD 信号
   API」。这是 4.2/4.3BSD 年代的惯用探针——**探的是宏，用的是 API 本体**，两者并无
   依赖关系。
2. `SIG_SETMASK` 是 POSIX.1 强制定义的宏（`sigprocmask()` 的 `how` 取值），任何
   libc 都有。OHOS sysroot 实测：

   ```text
   sysroot/usr/include/signal.h:32:#define SIG_SETMASK   2      ← 宏在
   grep -rlw sigvec sysroot/usr/include/ | wc -l  →  0           ← API 不在
   ```

3. 探测恒为真 → BSD 分支被选中 → `struct sigvec` 是不完整类型，编译即挂。
4. 这不是 OHOS 独有：本机 glibc 探针同样失败
   （`gcc -c` → `storage size of 'v' isn't known`），现代 glibc 也已移除 `sigvec`。
   差别在于 **musl/OHOS 没有任何 BSD 兼容兜底层**，`_BSD_SOURCE` /
   `_DEFAULT_SOURCE` 一类 feature test macro 救不回来，只能改代码。

## 修复

用 POSIX `sigaction` 取代整个 BSD 分支，不留平台宏：

```c
    struct sigaction sact ;     /* POSIX replacement for BSD sigvec */

    sact.sa_handler = exitsig ;
    sigfillset(&sact.sa_mask) ; /* == 原 sigvec 的 sv_mask = ~0 */
    sact.sa_flags = 0 ;         /* == 原 sv_flags = 0 */
    ...
        sigaction(i, &sact, NULL) ;
```

语义映射：

| BSD `struct sigvec` | POSIX `struct sigaction` | 含义 |
|---|---|---|
| `sv_handler` | `sa_handler` | 处理函数 |
| `sv_mask = ~0` | `sigfillset(&sa_mask)` | 处理器执行期间屏蔽所有信号 |
| `sv_flags = 0` | `sa_flags = 0` | 无特殊行为 |

`~0` 只有 32 位，`sigset_t` 覆盖全部信号号，替换后语义不劣于原实现。

## 与发行版做法的对比

Debian `socket 1.1-10.1` 的 `debian.patch` 走的是**降级路线**：把探测宏改名成
`BSD_SIG_SETMASK`（永不定义），让代码落进 `#else` 的裸 `signal(i, exitsig)` 分支。

```diff
-#ifdef SIG_SETMASK		/* only with BSD signals */
+#ifdef BSD_SIG_SETMASK		/* only with BSD signals */
     static struct sigvec svec = { exitsig, ~0, 0 } ;
 #endif
```

能编过，但丢掉了处理器执行期间的信号屏蔽字，且 `signal()` 的重入/重置语义在各 libc
上并不统一。本次适配选 `sigaction`，保住上游 `~0` 掩码的原意。

## 预判与验证

交叉编译前预扫，命中即知道要打这类补丁：

```bash
grep -rn "sigvec\|sigblock\|sigsetmask\|sigpause" src/
```

根因探针（两个 libc 对照）：

```bash
printf '#include <signal.h>\nint main(void){struct sigvec v;(void)v;return 0;}\n' > /tmp/p.c
gcc -c /tmp/p.c                                 # glibc: storage size of 'v' isn't known
aarch64-unknown-linux-ohos-clang -c /tmp/p.c    # musl : incomplete type 'struct sigvec'
```

修复后验证（socket 1.1 实测）：`conan create` 全绿；`test_package` 在
`qemu-aarch64` 下运行时 7/7 通过，其中 SIGTERM 用例**直接检验新装的 handler**——
退出码 241（= 256 + (−SIGTERM)）且 stderr 打印信号名，证明 `sigaction` 确实生效，
而不仅仅是「编译通过」。

## 适用范围

任何 4.2/4.3BSD 年代、以 `#ifdef SIG_SETMASK` 选择信号 API 的 C 程序，面向 OHOS/musl
编译时必触发。同族风险：同期的网络/终端小工具（BSD 风格 daemon、老 telnet/ftp 衍生
工具，以及 `sigvec`/`sigblock`/`sigsetmask`/`sigpause` 一族 API 的使用者）。

## 查重证据

- `engine` 对本错误签名的最近命中是 **E102**（OHOS 缺 `mmsghdr`/`recvmmsg`，
  同样报 incomplete type）——但 E102 的根因是**平台宏 `__linux__` 误判**、API 家族是
  批量消息，与「POSIX 宏被当作 BSD 特性探针」不同，修法（`!defined(__OHOS__)` 条件编译）
  也不适用于本例。
- `knowledge/` 全库（正式条目 + drafts）`grep -rli sigvec` 命中 0 条。
- 已有草稿 `pcapfix-1.1.7-musl-legacy-uint-bsd-types` 讲的是 musl 缺 legacy BSD
  **定宽类型别名**，属同一大类（musl 无 BSD 兼容层）但不同表征与修法，不构成重复。
