# es-shell 0.9.2：OHOS 运行时预装崩溃/回溯信号处理器，启动期检查 sa_handler 的程序 panic

> 草稿（DRAFT）— 来自 es-shell 0.9.2 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 knowledge/drafts/DRAFT-es-shell-0.9.2-ohos-prestalled-signal-handlers.kv

## 问题

es-shell 0.9.2 的 trip 回归测试（`make test`）在启动即 panic：

```
es panic: initsignals: bad incoming signal value for sigill: -796b7efc
```

`initsignals()` 逐个调用 `sigaction(sig, NULL, &sa)` 检查既有 handler，
一旦遇到既非 `SIG_DFL` 也非 `SIG_IGN` 也非 `SIG_ERR` 的 handler 就 panic。

## 根因

OHOS/HarmonyOS 运行时（libc / hnp 启动链路）在 `main()` 之前为以下信号
**预装了自己的崩溃/回溯 handler**（用探针实测，`sigaction(sig,NULL,&sa)`
返回的非标准 handler 包括）：

| 信号 | 含义 |
|------|------|
| 4 (SIGILL) | 非法指令（运行时非法指令陷阱） |
| 11 (SIGSEGV) | 段错误（崩溃报告/回溯） |
| 31 (SIGSYS) | 系统调用未实现（seccomp 类） |
| 36/37/42/44 | 若干实时信号（运行时内部） |

es-shell 把这些"既有但非默认"的 handler 视为环境被污染 → panic。
在 Linux 上这种场景几乎不存在，所以上游从未遇到。

## 解决方案

把"既有非默认 handler"视为 `sig_default`（平台运行时占用），继续由
`esignal()` 安装 es 自身管理的 handler，而非 panic：

```c
else if (h == SIG_DFL || h == SIG_ERR)
    sigeffect[sig] = sig_default;
else
    /* OHOS/HarmonyOS runtime pre-installs crash/backtrace handlers
       for SIGILL, SIGSEGV, SIGSYS and realtime signals before the
       shell starts. Treat pre-installed handlers as default effect
       instead of panicking. */
    sigeffect[sig] = sig_default;
```

## 验证

```bash
# 探针
for sig in 1..64: sigaction(sig,NULL,&sa) → 非 DFL/IGN/ERR 计 7 个（sig=4/11/31/36/37/42/44）
# 修复后
make test   # trip 回归通过（panic 消失）
```

## 适用边界

- OHOS/HarmonyOS 上所有启动期遍历信号表、检查既有 handler 的程序（shell、
  守护进程、init 工具、监控程序）都受影响；
- 若程序必须保留运行时回溯能力，需把既有 handler 存表并在自身退出/转发时
  调用，但 shell 类程序通常完全接管信号，视为默认即可；
- Linux/其他平台无运行时预装 handler，放宽检查不影响其语义。

## 反例 / 限制

- 不允许用 `#define SIGILL 0` 或空壳 stub 掩盖（R8）：必须保留实质信号处理；
- 若 panic 的 handler 其实是**程序自己**之前装的（非平台），需另行排查
  （本候选仅针对"平台预装"）。