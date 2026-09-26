# E634 — 4.2BSD 信号接口 sigvec/sigblock/sigsetmask/sigmask 在 OHOS musl 缺失

- 软件实证：multitee 3.0（Daniel J. Bernstein，1991，sigdfl.c / sigsched.c）
- 阶段：交叉编译（OHOS clang 15，musl sysroot）
- 日期：2026-09-23

## 错误特征

```text
sigdfl.c:30:16: error: variable has incomplete type 'struct sigvec'
sigdfl.c:31:16: error: variable has incomplete type 'struct sigvec'
sigdfl.c:32:16: error: variable has incomplete type 'struct sigvec'
sigdfl.c:46:12: warning: call to undeclared function 'sigblock'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
sigdfl.c:52:6: warning: call to undeclared function 'sigvec'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
sigdfl.c:69:2: warning: call to undeclared function 'sigsetmask'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
sigdfl.c:69:15: warning: call to undeclared function 'sigmask'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
sigsched.c:365:16: error: variable has incomplete type 'struct sigvec'
```

`struct sigvec` 是硬错误；其余三者在 OHOS clang 15 下只是告警，若只压掉 `struct sigvec`
也会在链接期报缺符号。

## 触发条件

- 构建系统：任意（本例是上游无构建文件、补丁新增的最小 Makefile）
- 阶段：compilation（链接期同样会暴露）
- 源码特征：`struct sigvec`、`sigvec()`、`sigblock()`、`sigsetmask()`、`sigmask()`，
  常伴随 `typedef int sigc_set;` 一类用 int 位图充当信号集的写法

## 根因分析

这组接口来自 4.2BSD，从未进入 POSIX。musl（OHOS 的 libc）一个都不提供，
glibc 2.21 起也删除了 `sigvec`。因此与编译器、构建系统无关：头文件里没有
`struct sigvec` 的定义，libc 里没有这些符号。

## 解决方案

### 推荐方案：逐点改写为 POSIX（不加平台宏）

| BSD 写法 | POSIX 写法 |
|---|---|
| `struct sigvec v; v.sv_handler = h; v.sv_mask = ~0; v.sv_flags = 0;` | `struct sigaction a; a.sa_handler = h; sigfillset(&a.sa_mask); a.sa_flags = 0;` |
| `sigvec(sig, &v, &old)` | `sigaction(sig, &a, &old)` |
| `old = sigblock(0); sigblock(~0);` | `sigfillset(&all); sigprocmask(SIG_BLOCK, &all, &old);` |
| `sigsetmask(~(sigmask(a) \| sigmask(b)))` | `sigfillset(&m); sigdelset(&m, a); sigdelset(&m, b); sigprocmask(SIG_SETMASK, &m, NULL);` |
| `sigsetmask(old)` | `sigprocmask(SIG_SETMASK, &old, NULL)` |
| `typedef int sigc_set;` + `1 << (i-1)` 位运算 | `typedef sigset_t sigc_set;` + `sigaddset`/`sigemptyset`/`sigismember(x,i) == 1` |
| `sv_flags` 不含 `SV_INTERRUPT`（BSD 默认：自动重启慢速系统调用） | `sa_flags = SA_RESTART` |
| `sv_flags` 含 `SV_INTERRUPT` | 不设 `SA_RESTART` |
| `sv_flags` 含 `SV_ONSTACK` | 加 `SA_ONSTACK` |
| `sv_flags` 含 `SV_RESETHAND` | 加 `SA_RESETHAND` |

三处容易漏的细节：

1. handler 签名改为 `void (*)(int)`（原 `static sigcont()` 是隐式 int、无参）。
2. handler 置位、主流程 `while (!cont) ;` 忙等的标志要改成 `volatile sig_atomic_t`。
   1991 年的代码在不优化时能工作，`-O2/-O3` 下读操作会被外提成死循环。
3. `sv_flags = 0` 不能照抄成 `sa_flags = 0`。BSD 默认会重启被中断的 `read()/write()`，POSIX 的 0 则返回 `EINTR`。
   只有 handler 仅在 `select/pselect` 窗口触发（Linux 上 `select` 无论是否设 `SA_RESTART` 都不重启），
   或仅在无系统调用的忙等中触发时，0 才与 BSD 默认等价。multitee 的两处 handler 正是这种情况，
   所以补丁取 0；其他程序要逐个 handler 评估。

multitee 的 sigsched.c 作者当年已在注释里写出了 `sigprocmask(SIG_BLOCK, ...)` 的等价形式，
改写只是把注释变成代码。补丁没有平台宏，在 glibc/BSD 上同样成立。

### 回退方案

调用点极多时，可以在补丁里加一个私有兼容头，用 `sigprocmask`/`sigaction` 实现同名 static 包装。
包装只能覆盖 1–32 号信号（int 掩码），所以只作兜底。

### 禁止做法

- ❌ `#define sigvec(...) 0`、`#define sigblock(x) 0` 之类空宏，或加 `#ifdef __OHOS__` 空分支
- ❌ 靠 `-std=gnu89` / `-Wno-error=implicit-function-declaration` 压告警。缺的是定义和符号，压告警没有用
- 后果：信号处理器没装上，运行期行为会静默改变。以 multitee 为例，写断管时本应捕获 SIGPIPE、只打告警并继续其它输出，
  实际却被默认动作杀死

## 验证

```bash
# 诊断：定位调用点
grep -rnE 'struct sigvec|\bsig(vec|block|setmask|mask)[[:space:]]*\(' --include='*.[ch]' <src>
# 修复后：产物只引用 POSIX 信号符号
llvm-nm -u <binary> | grep -E 'sig(action|procmask|fillset|delset|addset|emptyset|ismember)'
```

运行期回归（multitee test_package）有两条：
- F7：`0-1,N` 的 fd 1 接到没有读端的管道。预期退出码为 0，stderr 打出 `cannot write descriptor 1`，
  fd N 收到完整数据。这说明 sigaction 装上的 SIGPIPE handler 生效
- F8：`0:1` 接到同样的断管。预期进程死于 SIGPIPE（returncode −13），这说明 sigdfl() 改写后的
  `sigaction(SIG_DFL) + kill() + sigprocmask()` 路径正确

两项在同源 `.o` 静态重链副本上用 qemu-aarch64 实跑均通过（参见 E635）；OHOS CI worker 上由 test_package 原生执行。

## 关联条目

- 相似：E102（musl 缺少 Linux 专有 mmsg API，同属"libc 接口缺失需源码改写"一类）
- 原则：P005（补丁可向上游提交，因此用 POSIX 等价写法，不加平台宏）、P015（行为差异要做源码适配）
